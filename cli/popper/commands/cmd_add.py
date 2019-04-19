import os

import click
from popper import utils as pu
from popper.cli import pass_context
from popper.gha import Workflow


@click.command('add', short_help='Import workflow from remote repo.')
@click.argument('path', required=True)
@pass_context
def cli(ctx, path):
    """Imports a workflow from a remote project to the current directory,
    placed on the given path.
    """
    try:
        Workflow.import_from_repo(path, os.getcwd())
    except Exception:
        pu.fail('Failed to import from {} !'.format(path))
