import os
import re
import sys

import click

import popper.cli
from popper.cli import pass_context, log
from popper.gha import WorkflowRunner
from popper.parser import Workflow
from popper import utils as pu, scm
from popper import log as logging


@click.command(
    'run', short_help='Run a workflow or action.')
@click.argument(
    'action_wfile', required=False)
@click.option(
    '--on-failure',
    help='The action to run if there is a failure.',
    required=False,
    default=None
)
@click.option(
    '--with-dependencies',
    help='Run the action with all its dependencies.',
    required=False,
    is_flag=True
)
@click.option(
    '--workspace',
    help='Path to workspace folder.',
    required=False,
    show_default=True,
    default=popper.scm.get_git_root_folder()
)
@click.option(
    '--reuse',
    help='Reuse containers between executions (persist container state).',
    required=False,
    is_flag=True,
)
@click.option(
    '--skip',
    help=('Skip the list of actions/workflow specified.'),
    required=False,
    default=list(),
    multiple=True
)
@click.option(
    '--recursive',
    help='Run any .workflow file found recursively from current path.',
    required=False,
    is_flag=True
)
@click.option(
    '--quiet',
    help='Do not print output generated by actions.',
    required=False,
    is_flag=True
)
@click.option(
    '--debug',
    help=(
        'Generate detailed messages of what popper does (overrides --quiet)'),
    required=False,
    is_flag=True
)
@click.option(
    '--dry-run',
    help='A dry run for a workflow.',
    required=False,
    is_flag=True
)
@click.option(
    '--parallel',
    help='Executes actions in stages in parallel.',
    required=False,
    is_flag=True
)
@click.option(
    '--log-file',
    help='Path to a log file. No log is created if this is not given.',
    required=False
)
@click.option(
    '--skip-clone',
    help='Skip pulling docker or singularity images.',
    required=False,
    is_flag=True
)
@click.option(
    '--skip-pull',
    help='Skip cloning actions from github.',
    required=False,
    is_flag=True
)
@click.option(
    '--runtime',
    help='Specify the runtime where to execute the workflow.',
    type=click.Choice(['docker', 'singularity']),
    required=False,
    default='docker'
)
@pass_context
def cli(ctx, **kwargs):
    """Executes one or more pipelines and reports on their status.
    """
    if os.environ.get('CI') == 'true':
        log.info('Running in CI environment...')
        kwargs.update(parse_commit_message())
     
    # validate the options and return the workflows and actions to execute.
    wfile_list, action = validate_options(kwargs)
    kwargs.pop('recursive')
    kwargs.pop('action_wfile')
    print(wfile_list)
    # set the logging level.
    level = 'ACTION_INFO'
    
    if kwargs['quiet']:
        level = 'INFO'

    if kwargs['debug']:
        level = 'DEBUG'
    
    log.setLevel(level)
    
    if kwargs['log_file']:
        logging.add_log(log, kwargs['log_file'])

    if not wfile_list:
        log.fail('No workflows to execute.')

    kwargs.pop('debug')
    kwargs.pop('quiet')
    kwargs.pop('log_file')

    # Run all the workflows in the list.
    for wfile in wfile_list:
        log.info("Found and running workflow at " + wfile)
        run_pipeline(action, wfile, **kwargs)

def run_pipeline(action, wfile, skip_clone, skip_pull, skip, workspace, reuse,
                 dry_run, parallel, with_dependencies, on_failure, runtime):

    # Initialize a Worklow. During initialization all the validation
    # takes place automatically.
    wf = Workflow(wfile)
    pipeline = WorkflowRunner(wf)

    # Saving workflow instance for signal handling
    popper.cli.interrupt_params['parallel'] = parallel

    if parallel:
        if sys.version_info[0] < 3:
            log.fail('--parallel is only supported on Python3')
        log.warn("Using --parallel may result in interleaved output. "
                 "You may use --quiet flag to avoid confusion.")

    try:
        pipeline.run(action, skip_clone, skip_pull, skip, workspace, reuse,
                     dry_run, parallel, with_dependencies, runtime)
    except SystemExit as e:
        if (e.code != 0) and on_failure:
            pipeline.run(on_failure, skip_clone, skip_pull, list(), workspace,
                         reuse, dry_run, parallel, with_dependencies, runtime)
        else:
            raise

    if action:
        log.info('Action "{}" finished successfully.'.format(action))
    else:
        log.info('Workflow finished successfully.')


def parse_commit_message():
    head_commit = scm.get_head_commit()

    if not head_commit:
        return {}

    msg = head_commit.message

    if 'Merge' in msg:
        log.info("Merge detected. Reading message from merged commit.")
        if len(head_commit.parents) == 2:
            msg = head_commit.parents[1].message
    
    if not 'popper:[' in msg:
        return {}

    pattern = r'popper:\[(.+?)\]'
    try:
        args = re.search(pattern, msg).group(1).split(' ')
    except AttributeError:
        log.fail("The head commit message should contain a keyword "
                 "of the form 'popper:[...]'")
    
    ci_context = popper.commands.cmd_run.cli.make_context('popper run', args)
    return ci_context.params


def validate_options(kwargs):
    """Validate the options passed to run command.
    """
    def is_workflow(ref):
        """Check whether a given ref is a workflow.
        """
        if isinstance(ref, str):
            return ref.endswith('.workflow')
        elif isinstance(ref, list):
            for r in ref:
                if not r.endswith('.workflow'):
                    return False
        return True

    def is_action(ref):
        """Check whether a given ref is an action.
        """
        return not is_workflow(ref)

    action_wfile = kwargs.get('action_wfile')
    skip = kwargs.get('skip')
    with_dependencies = kwargs.get('with_dependencies')
    recursive = kwargs.get('recursive')

    wfile_list, action = list(), None

    if action_wfile and skip:
        # when both action_wfile and skip is given,
        # it is valid only when action_wfile is a workflow,
        # and skip consists of actions.
        if not(is_workflow(action_wfile) and is_action(skip)):
            log.fail('This arrangement does not make any sense.')

        if with_dependencies:
            log.fail('Cannot use --with-dependencies when action argument is not passed.')

        wfile_list = [action_wfile]

    elif action_wfile and not skip:
        # when action_wfile in given but not skip.
        if is_workflow(action_wfile):
            if with_dependencies:
                log.fail('Cannot use --with-dependencies when action argument is not passed.')
            if recursive:
                log.fail('Cannot run in recursive mode when workflow argument is passed.')
            wfile_list = [action_wfile]

        elif is_action(action_wfile):
            if recursive:
                log.fail('Cannot specify action to run in recursive mode.')
            wfile_list = pu.find_default_wfile()
            action = action_wfile

    elif not action_wfile and skip:
        # when action_wfile is not passed but skip is passed.
        if is_workflow(skip):
            if not recursive:
                log.fail('Cannot skip workflows in non-recursive mode.')
            wfile_list = set(pu.find_recursive_wfile()) - set(skip)
            wfile_list = list(wfile_list)

        elif is_action(skip):
            if recursive:
                wfile_list = pu.find_recursive_wfile()
            else:
                wfile_list = pu.find_default_wfile()
    else:
        # when action_wfile and skip, nothing is not passed.
        if with_dependencies:
            log.fail('Cannot use --with-dependencies when action argument is not passed.')
        if recursive:
            wfile_list = pu.find_recursive_wfile()
        else:
            wfile_list = pu.find_default_wfile()

    return wfile_list, action
