from __future__ import unicode_literals
from copy import deepcopy
from builtins import str, dict

import hcl

from popper.cli import log
from popper import utils as pu


VALID_ACTION_ATTRS = ["uses", "args", "needs", "runs", "secrets", "env"]
VALID_WORKFLOW_ATTRS = ["resolves", "on"]


def list_of_strings(arr):
    """Utility function to check whether a list consists of only
    strings or not.

    Args:
        arr (list) : The list to verify.

    Returns:
        bool : Whether the list consists of only strings or not.
    """
    # Python 2 to 3 Compability
    try:
        basestring
    except UnboundLocalError:
        basestring = str
    return bool(arr) and isinstance(arr, list) and all(
        isinstance(elem, basestring) for elem in arr)


class Action(object):
    """Represent's an Action."""

    def __init__(self, name, **attrs):
        self.attrs = attrs
        self.name = name
        self.uses = attrs.get('uses', None)
        self.needs = attrs.get('needs', None)
        # self.needs = self.needs if self.needs else self.needs
        self.args = self._normalize(attrs.get('args', None))
        self.runs = self._normalize(attrs.get('runs', None))
        self.env = attrs.get('env', None)
        self.secrets = self._normalize(attrs.get('secrets', None))
        self.next = None
        
        self._validate_action_block()

    def _normalize(self, params):
        if not params:
            return None
        if isinstance(params, str):
            return params.split(" ")
        elif isinstance(params, list):
            return " ".join(params).split(" ")
        else:
            return params

    def _validate_action_block(self):
        """Validate the action attributes."""
        for key in self.attrs.keys():
            if key not in VALID_ACTION_ATTRS:
                log.fail(
                    'Invalid action attribute \'{}\' was found.'.format(key))

        if not self.uses:
            log.fail("[uses] attribute must be present.")

        if not isinstance(self.uses, str):
            log.fail("[uses] attribute must be a string.")

        if self.needs and not list_of_strings(self.needs):
            log.fail("[needs] attribute must be a string or list.")

        if self.runs and not list_of_strings(self.runs):
            log.fail("[runs] attribute must be a string or a list.")
        
        if self.args and not list_of_strings(self.args):
            log.fail("[args] attribute must be a string or a list.")

        if self.env and not isinstance(self.env, dict):
            log.fail("[env] attribute must be a dict.")

        if self.secrets and not list_of_strings(self.secrets):
            log.fail("[secrets] attribute must be a string or a list.")


class Workflow(object):
    """Represent's a immutable workflow.
    """

    def __init__(self, wfile):

        with open(wfile, 'r') as fp:
            self._parsed_wfile = hcl.load(fp)
            fp.seek(0)
            self._wfile_content = fp.readlines()
        
        # Check the workflow file for correct composition
        # of actions and workflow blocks.
        name, attrs = self._validate_wfile(self._parsed_wfile)

        self.actions = dict()
        self.root = None
        self.name = name
        self.attrs = attrs
        self.on = attrs.get('on', 'push')
        self.resolves = attrs.get('resolves', None)
        # self.resolves = [self.resolves] if self.resolves else None

        self._validate_workflow_block()
        self._wrap_actions(self._parsed_wfile['action'])
        self._complete_graph()

    ## Parent function to call all the workflow file validators.
    def _validate_wfile(self, parsed_wfile):
        """Validate the workflow file in 3 stages:
            * Check for multiple workflow blocks.
            * Check for duplicate action blocks.
        """
        self._check_workflow_blocks()
        self._check_action_blocks()
        return list(parsed_wfile['workflow'].items())[0]

    ## Functions for validating the entire `.workflow` file.
    def _check_workflow_blocks(self):
        """Checks whether the workflow file contains more than
        one workflow blocks. If True, it throws error."""
        wf_count = len(self._parsed_wfile.get('workflow', dict()).items())
        if wf_count != 1:
            log.fail('Only a single workflow block is allowed per workflow file.')

    def _check_for_empty_workflow(self):
        """Checks whether the actions that the workflow wants to resolve
        exists or not."""
        actions = set(map(lambda a: a[0], self._parsed_wfile['action'].items()))
        if not set(self.attrs['resolves']).intersection(actions):
            log.fail('Can\'t resolve any of the actions.')

    def _check_action_blocks(self):
        """Checks whether duplicate action blocks are
        present or not."""
        actions = self._parsed_wfile.get('action', None)
        if not actions:
            log.fail('At least one action block must be present.')

        parsed_acount = 0
        if self._parsed_wfile.get('action', None):
            parsed_acount = len(list(self._parsed_wfile['action'].items()))
        acount = 0
        for line in self._wfile_content:
            line = line.strip()
            if line.startswith('action '):
                acount += 1
        if parsed_acount != acount:
            log.fail('Duplicate action identifiers found.')

    ## Function to validate the attributes of the workflow block.
    def _validate_workflow_block(self):
        """Validate the workflow attributes."""
        for key in self.attrs.keys():
            if key not in VALID_WORKFLOW_ATTRS:
                log.fail(
                    'Invalid workflow attribute \'{}\' was found.'.format(key))

        if not self.resolves:
            log.fail('[resolves] attribute must be present.')

        if not list_of_strings(self.resolves):
            log.fail('[resolves] attribute must be a string or a list.')

        if self.on and not isinstance(self.on, str):
            log.fail('[on] attribute must be a string or a list.')

    ## Function to wrap the actions along with other metadata
    def _wrap_actions(self, actions_dict):
        """Validate the action part of the worflow and 
        initialize Action objects."""
        for name, attrs in actions_dict.items():
            action = Action(name, **attrs)
            self.actions[name] = action
            
    @pu.threadsafe_generator
    def get_stages(self):
        """Generator of stages. A stages is a list of actions that can be
        executed in parallel.
        """
        current_stage = self._workflow['root']

        while current_stage:
            yield current_stage
            next_stage = set()
            for n in current_stage:
                next_stage.update(
                    self._workflow['action'][n].get(
                        'next', set()))
            current_stage = next_stage

    ## Functions to generate and manipulate workflow graphs.
    def _complete_graph_util(self, entrypoint, nwd):
        """A GHA workflow is defined by specifying edges that point to the
        previous nodes they depend on. To make the workflow easier to process,
        we add forward edges. This also obtains the root nodes.

        Args:
            entrypoint (list): List of nodes from where to start
                               generating the graph.
            nwd (set) : Set of nodes without dependencies.
        """
        for node in entrypoint:
            if self.actions.get(node, None):
                if self.actions[node].needs:
                    for n in self.actions[node].needs:
                        self._complete_graph_util([n], nwd)
                        if not self.actions[n].next:
                            self.actions[n].next = set()
                        self.actions[n].next.add(node)
                else:
                    nwd.add(node)
            else:
                log.fail('Action {} doesn\'t exist.'.format(node))

    def _complete_graph(self):
        """Driver function to run the recursive function
        `_complete_graph_util()` which adds forward edges.
        """
        print(self.resolves)
        self._check_for_empty_workflow()
        nodes_without_dependencies = set()
        self._complete_graph_util(self.resolves, nodes_without_dependencies)
        self.root = nodes_without_dependencies

    def check_for_unreachable_actions(self, skip=None):
        """Validates a workflow by checking for unreachable nodes / gaps
        in the workflow.

        Args:
            skip (list) : The list actions to skip if applicable.
        """

        def _traverse(entrypoint, reachable, workflow):
            for node in entrypoint:
                reachable.add(node)
                _traverse(workflow['action'][node].get(
                    'next', []), reachable, workflow)

        reachable = set()
        skipped = set(self._workflow['props'].get('skip_list', []))
        actions = set(map(lambda a: a[0], self._workflow['action'].items()))

        _traverse(self._workflow['root'], reachable, self._workflow)

        unreachable = actions - reachable
        if unreachable - skipped:
            if skip:
                log.fail('Actions {} are unreachable.'.format(
                    ', '.join(unreachable - skipped))
                )
            else:
                log.warn('Actions {} are unreachable.'.format(
                    ', '.join(unreachable))
                )

        for a in unreachable:
            self._workflow['action'].pop(a)

    @staticmethod
    def skip_actions(wf, skip_list=list()):
        """Removes the actions to be skipped from the workflow graph and
        return a new `Workflow` object.

        Args:
            wf (Workflow) : The workflow object to operate upon.
            skip_list (list) : List of actions to be skipped.

        Returns:
            Workflow : The updated workflow object.
        """
        workflow = deepcopy(wf)
        for sa_name in skip_list:

            # Isolate the skipped actions totally.
            sa_block = workflow.get_action(sa_name)
            sa_block['next'].clear()
            sa_block['needs'].clear()

            # Handle skipping of root action's
            if sa_name in workflow.root:
                workflow.root.remove(sa_name)

            # Handle skipping of not-root action's
            for a_name, a_block in workflow.actions.items():

                if sa_name in a_block.get('next', set()):
                    a_block['next'].remove(sa_name)
                
                if sa_name in a_block.get('needs', list()):
                    a_block['needs'].remove(sa_name)

        workflow.props['skip_list'] = list(skip_list)
        return workflow

    @staticmethod
    def filter_action(wf, action, with_dependencies=False):
        """Filters out all actions except the one passed in
        the argument from the workflow.

        Args:
            wf (Workflow) : The workflow object to operate upon.
            action (str) : The action to run.
            with_dependencies (bool) : Filter out action to
            run with dependencies or not.

        Returns:
            Workflow : The updated workflow object.
        """
        # Recursively generate root when an action is run
        # with the `--with-dependencies` flag.
        def find_root_recursively(workflow, action, required_actions):
            required_actions.add(action)
            if workflow.get_action(action).get('needs', None):
                for a in workflow.get_action(action)['needs']:
                    find_root_recursively(workflow, a, required_actions)
                    if not workflow.get_action(a).get('next', None):
                        workflow.get_action(a)['next'] = set()
                    workflow.get_action(a)['next'].add(action)
            else:
                workflow.root.add(action)

        # The list of actions that needs to be preserved.
        workflow = deepcopy(wf)

        actions = set(map(lambda x: x[0], workflow.actions.items()))

        required_actions = set()

        if with_dependencies:
            # Prepare the graph for running only the given action
            # only with its dependencies.
            find_root_recursively(workflow, action, required_actions)

            filtered_actions = actions - required_actions

            for ra in required_actions:
                a_block = workflow.get_action(ra)
                common_actions = filtered_actions.intersection(
                    a_block.get('next', set()))
                if common_actions:
                    for ca in common_actions:
                        a_block['next'].remove(ca)
        else:
            # Prepare the action for its execution only.
            required_actions.add(action)

            if workflow.get_action(action).get('next', None):
                workflow.get_action(action)['next'] = set()

            if workflow.get_action(action).get('needs', None):
                workflow.get_action(action)['needs'] = list()

            workflow.root.add(action)

        # Make the list of the actions to be removed.
        actions = actions - required_actions

        # Remove the remaining actions
        for a in actions:
            if a in workflow.root:
                workflow.root.remove(a)
            workflow.actions.pop(a)

        return workflow
