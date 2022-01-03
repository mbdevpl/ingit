"""Command-line interface of ingit."""

import argparse
import logging
import pathlib

import argcomplete

from .config_boilerplate import initialize_config_directory
from .cli_boilerplate import \
    ArgumentDefaultsAndRawDescriptionHelpFormatter, make_copyright_notice, add_version_option, \
    add_verbosity_group, get_verbosity_level, dedent_except_first_line
from .json_config import RUNTIME_CONFIG_PATH, REPOS_CONFIG_PATH
from .runtime import Runtime

_LOG = logging.getLogger(__name__)

PREDICATE_EXAMPLES = ['''name.startswith('py_')''', ''' 'python' in tags''']

REGEX_EXAMPLES = ['^py_.*', '^python$']

SUGGESTED_TAGS = [
    'appveyor', 'archived', 'assembla', 'bash', 'bitbucket', 'c', 'c++', 'c#', 'css', 'cython',
    'docker', 'fortran', 'gist', 'github', 'html', 'java', 'latex', 'opencl', 'php', 'python',
    'ruby', 'travis', 'vsonline']

OUT = logging.getLogger('ingit.interface.print')


def prepare_parser():
    """Prepare command-line arguments parser."""
    parser = argparse.ArgumentParser(
        prog='ingit',
        description='''Tool for managing a large collection of repositories in git. If you have
        100 git-versioned projects, keeping tabs on everything can be quite troublesome.''',
        epilog=make_copyright_notice(
            2015, 2022, license_name='GNU General Public License v3 or later (GPLv3+)',
            url='https://github.com/mbdevpl/ingit'),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter, allow_abbrev=True)
    add_version_option(parser)

    interactivity_group = parser.add_mutually_exclusive_group(required=False)
    interactivity_group.add_argument(
        '--batch', '--non-interactive', dest='batch', action='store_true',
        help='run ingit in non-interactive mode')
    interactivity_group.add_argument(
        '--interactive', dest='batch', action='store_false',
        help='force interactive mode even if configuration sets batch mode as default')
    parser.set_defaults(batch=None)

    add_verbosity_group(parser)

    parser.add_argument(
        '--config', metavar='PATH', type=str, default=str(RUNTIME_CONFIG_PATH),
        help='''path to the runtime configuration file;
        can be absolute, or relative to current woking directory''')

    parser.add_argument(
        '--repos', metavar='PATH', type=str, default=str(REPOS_CONFIG_PATH),
        help='''path to the projects list file;
        can be absolute, or relative to current woking directory''')

    parser.add_argument(
        '--predicate', '-p', type=str, default=None, help=f'''a Python expression used to select
        repositories operated on; it is evaluated on each repository metadata;
        examples: "{'", "'.join(PREDICATE_EXAMPLES)}"''')
    parser.add_argument(
        '--regex', '-r', type=str, default=None, help=f'''a regular expression used to select
        repositories operated on; repository matches if any of its metadata match;
        examples: "{'", "'.join(REGEX_EXAMPLES)}"''')

    commands = {
        'summary': (
            'show summary of registered repositories and status of configured repository root',
            '''First of all, print a list of registered repositories. By default, all
            registered repositories are listed, but, as in case of most commands, the
            results can be filtered via a predicate or regex.

            Independently, print a list of all unregistered repositories and all not
            versioned paths present in the configured repositories root.'''),
        'register': (
            'start tracking a repository in ingit',
            '''The initial configuration is set according to basic repository information:
            its root directory name becomes "name" and its currently configured remotes
            become "remotes". You can edit the configuration manually afterwards.

            The final "path" to the repository stored in the configuration depends on the
            "repos_path" in runtime configuation. The configured "path" will be:

            *   resolved absolute path if there is no "repos_path" configured or
                repository path is outside of the "repos_path";
            *   resolved relative path to the "repos_path", if the repository path is
                within it;
            *   nothing (i.e. not stored) if the if the repository is stored directly in
                "repos_path" (i.e. there are no intermediate directories).

            Behaviour of storing relative/no paths in some cases is implemented to make
            configuration file much less verbose in typical usage scenarios. To prevent
            this behaviour, and force all repository paths to be absolute, simply set the
            "repos_path" in your runtime configuraion to JSON "null".'''),
        'foreach': (
            'execute a custom command',
            '''The given command is executed in a shell in working directory of each
            project.'''),
        'clone': (
            'perform git clone',
            '''Execute "git clone <remote-url> --recursive --orign <remote-name> <path>",
            where values of <path> and <remote-...> are taken from default remote
            configuration of the repository.

            After cloning, add all remaining configured remotes to the repository and
            fetch them.'''),
        'init': (
            'perofrm git init',
            '''Execute "git init", followed by "git remote add" for each configured
            remote.'''),
        'fetch': (
            'perform git fetch',
            '''Execute "git fetch <remote-name>", where the remote name is the remote of
            the current　tracking branch, or all remotes of the repository if there's no
            tracking branch,　or repository is in detached head state.'''),
        'checkout': (
            'perform git checkout',
            '''Interactively select revision to checkout from list of local branches, remote
            non-tracking branches and local tags.

            The list of branches to select from is composed by combining:

            *   local branches
            *   non-tracking branches on all remotes
            *   local tags

            Checking out a remote branch will create a local branch with the same unless
            it already exists. If it already exists, repository will end up in detached
            head state.

            Also, checking out any tag will put repository in a detached head state.'''),
        'merge': (
            'perform git merge (not yet implemented)',
            '''Not yet implemented! The following functionality is intended.

            Interactively merge all branches to their tracking branches. For each not
            merged <branch>-<tracking-branch> pair, execute
            "git checkout <branch>" and then if the merge is fast-forward,
            automatically execute "git merge <tracking-branch> --ff-only". If not, then
            show more information about the situation of the repository, and propose:

            *   "git merge --log <tracking-branch>",
            *   "git rebase -i <tracking-branch>" and
            *   "git reset --hard <tracking-branch>".

            If repository is dirty when this command is executed, do nothing. After work
            is done, return to the originally checked-out branch.'''),
        'push': (
            'perform git push (not yet fully implemented)',
            '''Execute "git push <remote-name> <branch>:<tracking-branch-name>" for the
            active branch.'''),
        'gc': ('perform git gc', 'Execute "git gc --agressive --prune".'),
        'status': (
            'perform git status, as well as other diagnostic git commands',
            '''Perform git status, as well as other diagnostic git commands.

            Execute:

            *   "git status --short --branch" to inform about any uncommitted changes,
            *   "git log tracking_branch..branch" to inform about commits that are not
                yet pushed to the remote,
            *   "git log branch..tracking_branch" to inform about commits that are not
                yet merged from the remote.

            Additionally, compare registered remotes with actual remotes to make sure
            that ingit configuration is in sync with the repository metadata..''')}

    subparsers = parser.add_subparsers(
        dest='command', metavar='command', help=f'''main command to execute; one of:
        "{'", "'.join(commands.keys())}";
        run "ingit command --help" to see detailed help for a given command''')

    _prepare_command_subparsers(subparsers, commands)
    argcomplete.autocomplete(parser)

    return parser


def _prepare_command_subparsers(subparsers, commands):
    for command, (help_, description) in commands.items():
        subparser = subparsers.add_parser(
            command, help=help_, formatter_class=ArgumentDefaultsAndRawDescriptionHelpFormatter)
        subparser.description = dedent_except_first_line(description)
        if command == 'register':
            subparser.add_argument(
                '--tags', metavar='TAG', type=str, default=None, nargs='+',
                help='set tags for this repository, they will be added to initial configuration') \
                .completer = argcomplete.completers.ChoicesCompleter(choices=SUGGESTED_TAGS)
            subparser.add_argument(
                'path', metavar='PATH', type=str, nargs='?',
                help='''path to root directory of repository, use current working directory
                if not provided''')
        elif command == 'foreach':
            subparser.add_argument(
                'cmd', metavar='COMMAND', type=str,
                help='command to be executed in shell in working directory of each project')
            # subparser.add_argument(
            #     '--recursive', action='store_true',
            #     help='(not yet implemented)')
            subparser.add_argument(
                '--timeout', metavar='SECONDS', type=float, default=None,
                help='timeout of the command (in seconds)')
        elif command == 'fetch':
            subparser.add_argument(
                '--all', action='store_true',
                help='fetch all remotes in all cases')
        elif command == 'push':
            subparser.add_argument(
                '--all', action='store_true',
                help='''(not yet implemented) execute the push for every branch that has a remote
                tracking branch''')
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
        command_options['timeout'] = parsed_args.timeout
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
        parser.error(f'project filtering is not applicable to "{parsed_args.command}" command'
                     ' -- it can be used only with summary command and with git-like commands')

    level = logging.CRITICAL - 10 * get_verbosity_level(parsed_args)
    OUT.setLevel(level)
    assert level == OUT.getEffectiveLevel(), (level, OUT.getEffectiveLevel())

    OUT.info('parsed args: %s', parsed_args)

    initialize_config_directory('ingit')

    runtime_config_path = pathlib.Path(parsed_args.config)
    repos_config_path = pathlib.Path(parsed_args.repos)

    if parsed_args.predicate is None:
        predicate = None
    else:
        predicate_code = f"lambda name, tags, path, remotes: ({parsed_args.predicate})"
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
