"""Command-line interface of ingit."""

import argparse
import logging
import pathlib
import sys

from ._version import VERSION
from .json_config import RUNTIME_CONFIG_PATH, REPOS_CONFIG_PATH
from .runtime import Runtime

_LOG = logging.getLogger(__name__)

PREDICATE_EXAMPLES = ['''name.startswith('py_')''', ''' 'python' in tags''']

REGEX_EXAMPLES = ['^py_.*', '^python$']

OUT = logging.getLogger('ingit.interface.print')


def prepare_parser():
    """Prepare command-line arguments parser."""

    parser = argparse.ArgumentParser(
        prog='ingit',
        description='''Tool for managing a large collection of repositories in git. If you have
        100 git-versioned projects, keeping tabs on everything can be quite troublesome.''',
        epilog='''Copyright (C) 2015-2018 by Mateusz Bysiek,
        GNU General Public License v3 or later (GPLv3+), https://github.com/mbdevpl/ingit''',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter, allow_abbrev=True)
    parser.add_argument('--version', action='version',
                        version='ingit {}, Python {}'.format(VERSION, sys.version))

    interactivity_group = parser.add_mutually_exclusive_group(required=False)
    interactivity_group.add_argument(
        '--batch', '--non-interactive', dest='batch', action='store_true',
        help='run ingit in non-interactive mode')
    interactivity_group.add_argument(
        '--interactive', dest='batch', action='store_false',
        help='force interactive mode even if configuration sets batch mode as default')
    parser.set_defaults(batch=None)

    verbosity_group = parser.add_mutually_exclusive_group(required=False)
    verbosity_group.add_argument(
        '--verbose', '-v', action='count',
        help='ingit should be more verbose than by default'
        ' (repeat up to 2 times for stronger effect)')
    verbosity_group.add_argument(
        '--quiet', '-q', action='count',
        help='ingit should be more quiet than by default'
        ' (repeat up to 3 times for stronger effect)')
    verbosity_group.add_argument(
        '--verbosity', metavar='LEVEL', type=int, default=logging.CRITICAL - logging.WARNING,
        help='set verbosity level explicitly (normally from {} to {})'
        .format(logging.CRITICAL - logging.CRITICAL, logging.CRITICAL - logging.NOTSET))

    parser.add_argument(
        '--config', metavar='PATH', type=str, default=str(RUNTIME_CONFIG_PATH),
        help='''path to the runtime configuration file;
        can be absolute, or relative to current woking directory''')

    parser.add_argument(
        '--repos', metavar='PATH', type=str, default=str(REPOS_CONFIG_PATH),
        help='''path to the projects list file;
        can be absolute, or relative to current woking directory''')

    parser.add_argument(
        '--predicate', '-p', type=str, default=None, help='''a Python expression used to select
        repositories operated on; it is evaluated on each repository metadata;
        examples: "{}"'''.format('", "'.join(PREDICATE_EXAMPLES)))
    parser.add_argument(
        '--regex', '-r', type=str, default=None, help='''a regular expression used to select
        repositories operated on; repository matches if any of its metadata match;
        examples: "{}"'''.format('", "'.join(REGEX_EXAMPLES)))

    commands = {
        'summary': (
            'show summary of registered repositories and status of configured repository root',
            '''First of all, print a list of registered repositories. By default, all registered
            repositories are listed, but, as in case of most commands, the results can be filtered
            via a predicate or regex. Independently, print a list of all unregistered repositories
            and all not versioned paths present in the configured repositories root.'''),
        'register': (
            'start tracking a repository in ingit',
            '''The initial configuration is set according to basic repository information:
            its root directory name becomes "name",
            its absolute path becomes "path",
            and its currently configured remotes become "remotes".
            You can edit the configuration manually afterwards.'''),
        'foreach': (
            'execute a custom command',
            'The given command is executed in a shell in working directory of each project.'),
        'clone': (
            'perform git clone',
            '''Execute "git clone <remote-url> --recursive --orign <remote-name> <path>",
            where values of <path> and <remote-...> are taken from default remote configuration
            of the repository.
            After cloning, add all remaining configured remotes to the repository and fetch them.
            '''),
        'init': (
            'perofrm git init',
            'Execute "git init", followed by "git remote add" for each configured remote.'),
        'fetch': (
            'perform git fetch',
            '''Execute "git fetch <remote-name>", where the remote name is the remote of the current
            tracking branch, or all remotes of the repository if there's no tracking branch,
            or repository is in detached head state.'''),
        'checkout': (
            'perform git checkout',
            '''Interactively select revision to checkout from list of local branches,
            remote non-tracking branches and local tags.'''),
        'merge': (
            'perform git merge (not yet implemented)',
            '''Interactively merge all branches to their tracking branches.
            For each <branch>-<tracking-branch> pair,
            execute "git checkout <branch>" and then if the merge can be fast-forward,
            automatically execute "git merge <tracking-branch> --ff-only".
            If not, then show more information about the situation of the repository, and propose:
            "git merge --log <tracking-branch>", "git rebase -i <tracking-branch>" and
            "git reset --hard <tracking-branch>".
            If repository is dirty when this command is executed, the command will do nothing.
            After work is done, return to the originally checked-out branch.'''),
        'push': (
            'perform git push (not yet fully implemented)',
            '''Execute "git push <remote-name> <branch>:<tracking-branch-name>"
            for the active branch.'''),
        'gc': ('perform git gc', 'Execute "git gc --agressive --prune".'),
        'status': (
            'perform git status, as well as other diagnostic git commands',
            '''Execute git status --short --branch to inform about any uncommited changes,
            git log tracking_branch..branch to inform about commits that are not yet pushed
            to the remote, and
            git log branch..tracking_branch to inform about commits that are not yet merged
            from the remote.
            Additionally, compare registered remotes with actual remotes to make sure that ingit
            configuration is in sync with the repository metadata.''')}

    subparsers = parser.add_subparsers(
        dest='command', metavar='command', help='''main command to execute; one of: "{}";
        run "ingit command --help" to see detailed help for a given command'''
        .format('", "'.join(commands.keys())))

    _prepare_command_subparsers(subparsers, commands)

    return parser


def _prepare_command_subparsers(subparsers, commands):
    for command, (help_, description) in commands.items():
        subparser = subparsers.add_parser(command, help=help_)
        subparser.description = description
        if command == 'register':
            subparser.add_argument(
                '--tags', metavar='TAG', type=str, default=None, nargs='+',
                help='set tags for this repository, they will be added to initial configuration')
            subparser.add_argument(
                'path', metavar='PATH', type=str, nargs='?',
                help='''path to root directory of repository, use current working directory
                if not provided''')
        elif command == 'foreach':
            subparser.add_argument(
                'cmd', metavar='COMMAND', type=str,
                help='command to be executed in shell in working directory of each project')
            subparser.add_argument(
                '--recursive', action='store_true',
                help='')  # TODO: write help
            subparser.add_argument(
                '--timeout', metavar='SECONDS', type=int, default=None,
                help='')  # TODO: write help
        elif command == 'fetch':
            subparser.add_argument(
                '--all', action='store_true',
                help='fetch all remotes in all cases')
        elif command == 'push':
            subparser.add_argument(
                '--all', action='store_true',
                help='''execute the push for every branch that has a remote tracking branch
                (not yet implemented)''')
        elif command == 'status':
            subparser.add_argument(
                '-i', '--ignored', action='store_true',
                help='''include ignored files in the status report
                (identical to "--ignored" flag on "git status")''')


def _prepare_command_options(command, parsed_args):
    command_options = {}
    if command == 'register':
        command_options['tags'] = parsed_args.tags
        command_options['path'] = pathlib.Path(
            '.' if parsed_args.path is None else parsed_args.path)
    elif command == 'foreach':
        command_options['cmd'] = parsed_args.cmd
    elif command == 'fetch':
        command_options['all_remotes'] = parsed_args.all
    elif command == 'push':
        command_options['all_branches'] = parsed_args.all
    elif command == 'status':
        command_options['ignored'] = parsed_args.ignored
    return command_options


def main(args=None):
    """Parse command line arguments and run ingit accordingly."""

    parser = prepare_parser()
    parsed_args = parser.parse_args(args)
    if (parsed_args.predicate is not None or parsed_args.regex is not None) \
            and parsed_args.command == 'register':
        parser.error('project filtering is not applicable to "{}" command'
                     ' -- it can be used only with summary command and with git-like commands'
                     .format(parsed_args.command))

    level = logging.CRITICAL
    if parsed_args.verbose is not None:
        level -= 10 * parsed_args.verbose
    if parsed_args.quiet is not None:
        level += 10 * parsed_args.quiet
    if parsed_args.verbosity is not None:
        level -= parsed_args.verbosity
    OUT.setLevel(level)
    assert level == OUT.getEffectiveLevel(), (level, OUT.getEffectiveLevel())

    OUT.info('parsed args: %s', parsed_args)

    runtime_config_path = pathlib.Path(parsed_args.config)
    repos_config_path = pathlib.Path(parsed_args.repos)

    if parsed_args.predicate is None:
        predicate = None
    else:
        predicate_code = "lambda name, tags, path, remotes: ({})".format(parsed_args.predicate)
        _LOG.warning('prepared predicate lambda: %s', predicate_code)
        predicate = eval(predicate_code)

    if parsed_args.regex is None:
        regex = None
    else:
        regex = parsed_args.regex

    command = parsed_args.command
    if command is None:
        parser.error('no command provided')

    command_options = _prepare_command_options(command, parsed_args)

    interactive = None if parsed_args.batch is None else not parsed_args.batch
    runtime = Runtime(runtime_config_path, repos_config_path, interactive=interactive)

    if predicate is not None:
        runtime.filter_projects(predicate)
    if regex is not None:
        runtime.filter_projects(regex)
    runtime.execute(command, **command_options)

    # run(runtime_config_path, repos_config_path, predicate, regex, command, **command_options)
