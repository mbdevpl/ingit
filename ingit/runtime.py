"""The ingit runtime."""

import collections.abc
import functools
import logging
import pathlib
import platform
import re
import subprocess
import typing as t

from boilerplates.config import normalize_path
import git
import ordered_set

from .runtime_interface import ask
from .json_config import \
    json_to_file, default_machine_configuration, acquire_configuration, acquire_repos_configuration
from .repo_data import RepoData
from .project import Project

_LOG = logging.getLogger(__name__)


def regex_predicate(regex: str, name, tags, path, remotes):
    """Repo filtering function launched when "ingit -r 'regex' <command> ..." is used."""
    return (
        re.search(regex, name) is not None
        or any(re.search(regex, tag) is not None for tag in tags)
        or re.search(regex, str(path)) is not None
        or any(re.search(regex, name) for name, url in remotes.items()))


class Runtime:  # pylint: disable = too-many-instance-attributes
    """The ingit runtime."""

    def __init__(self, runtime_config_path: pathlib.Path, repos_config_path: pathlib.Path,
                 hostname: str | None = None, interactive: t.Optional[bool] = None):
        self.runtime_config_path = runtime_config_path
        self.repos_config_path = repos_config_path
        self._hostname = platform.node() if hostname is None else hostname
        self._interactive = interactive

        # prepare, possibly interactive
        self.runtime_config = acquire_configuration(self.runtime_config_path, 'runtime')
        self._machine_config = self._read_machine_config()

        self.repos_config = acquire_repos_configuration(self.repos_config_path)
        self.projects = self._read_projects()
        self.filtered_projects = list(self.projects)

    @property
    def repos_path(self):
        """Get path to where repositories are by default."""
        raw_path = self._machine_config['repos_path']
        if raw_path is None:
            return None
        return pathlib.Path(normalize_path(raw_path))

    @property
    def interactive(self):
        if self._interactive is None:
            return self._machine_config['interactive']
        return self._interactive

    def _read_machine_config(self):
        for machine in self.runtime_config['machines']:
            names = []
            assert ('name' in machine) ^ ('names' in machine), machine
            if 'name' in machine:
                names.append(machine['name'])
            else:
                names += machine['names']
            if '' in names or self._hostname in names:
                return machine

        ans = ask(f'No matching machine for "{self._hostname}" found in configuration. Add it?')
        if ans != 'y':
            raise ValueError(f'No matching machine for "{self._hostname}"'
                             f' found in configuration """{self.runtime_config}"""')
        machine = self.register_machine(self._hostname)
        return machine

    def _read_projects(self) -> t.Sequence[Project]:
        """Get list of all projects in repositories configuration."""
        projects = []
        for repo in self.repos_config['repos']:
            name = repo['name']
            assert not ('path' in repo and 'paths' in repo), repo
            raw_path = None
            if 'path' in repo:
                raw_path = repo['path']
            elif 'paths' in repo and self._hostname in repo['paths']:
                raw_path = repo['paths'][self._hostname]
            elif 'paths' in repo and '' in repo['paths']:
                raw_path = repo['paths']['']
            if raw_path is None:
                path = pathlib.Path(name)
            else:
                path = pathlib.Path(normalize_path(raw_path))
            if not path.is_absolute():
                if self.repos_path is None:
                    raise ValueError(f'configuration of repository "{name}" must contain absolute'
                                     ' path because repos_path in runtime configuration is not set')
                path = self.repos_path.joinpath(path)
            project = Project(name=name, tags=repo['tags'], path=path, remotes=repo['remotes'])
            projects.append(project)
        return projects

    def filter_projects(self, predicate: t.Union[collections.abc.Callable, str]):
        """Select subset of all of the projects registered projects for processing."""
        assert callable(predicate) or isinstance(predicate, str), type(predicate)
        if isinstance(predicate, str):
            predicate = functools.partial(regex_predicate, predicate)
        self.filtered_projects = [
            project for project in self.projects
            if predicate(project.name, project.tags, project.path, project.remotes)]

    def execute(self, command: str, **command_options):
        """Execute the runtime."""
        command_executor = {
            'summary': self.execute_ingit_command,
            'register': self.execute_ingit_command,
            'foreach': self.execute_ingit_command,
            'clone': self.execute_git_command,
            'init': self.execute_git_command,
            'fetch': self.execute_git_command,
            'checkout': self.execute_git_command,
            'merge': self.execute_git_command,
            'push': self.execute_git_command,
            'gc': self.execute_git_command,
            'status': self.execute_git_command}[command]

        command_executor(command, **command_options)

    def execute_ingit_command(self, command: str, **command_options):
        """Execute an ingit command, as opposed to a wrapper for a git built-in command."""
        command = {
            'summary': 'repositories_summary',
            'register': 'register_repository',
            'foreach': 'execute_command'}.get(command, command)
        implementation = getattr(self, command)
        implementation(**command_options)

    def execute_git_command(self, command: str, **command_options):
        """Execute a wrapper for a git built-in command."""
        command = {
            'gc': 'collect_garbage'}.get(command, command)
        for project in self.filtered_projects:
            implementation = getattr(project, command)
            try:
                implementation(**command_options)
            except RuntimeError:
                _LOG.exception('failed to execute command "%s" for project %s', command, project)

    def execute_command(self, cmd: str, timeout: t.Optional[int] = None):
        """Execute a command in each of the projects (after filtering was applied)."""
        for project in self.filtered_projects:
            if not project.path.is_dir():
                continue
            try:
                subprocess.run(cmd, check=True, timeout=timeout, shell=True, cwd=project.path)
            except subprocess.TimeoutExpired:
                _LOG.error(
                    'command "%s" in %s was aborted because it took too much time',
                    cmd, project)
            except subprocess.CalledProcessError as err:
                _LOG.error(
                    'command "%s" failed in %s:\nstderr: %s\nstdout: %s',
                    cmd, project, err.stderr, err.stdout)

    def repositories_summary(self):
        """Summarize registered repositories."""
        all_count = len(self.filtered_projects)
        was_filtered = all_count < len(self.repos_config['repos'])
        if was_filtered:
            print(f'Registered projects matching given conditions ({all_count}):')
        else:
            print(f'All registered projects ({all_count}):')
        initialised_count = 0
        for project in self.filtered_projects:
            if project.is_initialised:
                initialised_count += 1
            print(' -', project)

        if initialised_count == all_count:
            if all_count > 0:
                print('All of them are initialised.')
            else:
                print('')
        else:
            print(f'{initialised_count} of them are initialised'
                  f' ({all_count - initialised_count} not).')

        if self.repos_path is not None:
            self._unregistered_folders_summary()

    def _unregistered_folders_summary(self):
        assert self.repos_path is not None

        project_paths_in_root = ordered_set.OrderedSet()
        for project in self.projects:
            try:
                project_paths_in_root.add(project.path.relative_to(self.repos_path))
            except ValueError:
                pass

        unregistered_in_root, non_repo_paths_in_root = \
            self._find_unregistered_folders_in_root(project_paths_in_root)

        if unregistered_in_root:
            print(f'There are {len(unregistered_in_root)} unregistered git repositories'
                  f' in configured repositories root "{self.repos_path}".')
            for path in unregistered_in_root:
                print(path)

        if non_repo_paths_in_root:
            print(f'There are {len(non_repo_paths_in_root)} not versioned folders'
                  f' in configured repositories root "{self.repos_path}".')
            for path in non_repo_paths_in_root:
                print(path)

    def _find_unregistered_folders_in_root(self, project_paths_in_root: ordered_set.OrderedSet):
        assert self.repos_path is not None

        unregistered: ordered_set.OrderedSet[pathlib.Path] = ordered_set.OrderedSet()
        non_repo_paths: ordered_set.OrderedSet[pathlib.Path] = ordered_set.OrderedSet()
        for path in self.repos_path.iterdir():
            if not path.is_dir():
                continue
            try:
                _ = git.Repo(str(path))
            except git.InvalidGitRepositoryError:
                non_repo_paths.add(path)
                continue
            relative_path = path.relative_to(self.repos_path)
            if relative_path in project_paths_in_root:
                continue
            unregistered.add(path)
        return unregistered, non_repo_paths

    def register_machine(self, name: str) -> dict:
        """Add machine to ingit runtime configuration."""
        assert isinstance(name, str), type(name)
        assert name
        for machine in self.runtime_config['machines']:
            names = []
            if 'name' in machine:
                names.append(machine['name'])
            if 'names' in machine:
                names += machine['names']
            if '' in names or name in names:
                raise ValueError(f'machine "{name}" already in configuration')
        machine_config = default_machine_configuration(name)
        _LOG.warning('adding machine to configuration: %s', machine_config)
        self.runtime_config['machines'].append(machine_config)
        json_to_file(self.runtime_config, self.runtime_config_path)
        return machine_config

    def register_repository(self, path: pathlib.Path, tags: t.Sequence[str]):
        """Add repo to ingit repositories configuration."""
        repo = git.Repo(str(path))
        repo_data = RepoData(repo)
        repo_data.refresh()
        _LOG.debug('registering repository: %s', repo_data)
        repo_config = repo_data.generate_repo_configuration()

        self._postprocess_configured_repo_path(repo_config)

        if tags is not None:
            repo_config['tags'] += tags
        _LOG.warning('adding repo to configuration: %s', repo_config)
        index = None
        lowercase_name = repo_config['name'].lower()
        for i, project in enumerate(self.projects):
            lowercase_project_name = project.name.lower()
            if index is None and lowercase_project_name > lowercase_name:
                index = i
            if lowercase_project_name == lowercase_name:
                raise ValueError(
                    f'project named {project.name} already exists in current configuration')
        if index is None:
            index = len(self.projects)
        self.repos_config['repos'].insert(index, repo_config)
        json_to_file(self.repos_config, self.repos_config_path)

    def _postprocess_configured_repo_path(self, repo_config) -> None:
        try:
            absolute_repo_path = pathlib.Path(repo_config['path']).resolve()
        except ValueError:
            _LOG.info('cannot resolve repo path %s', repo_config['path'])
            return

        if self.repos_path is None:
            _LOG.warning(
                'repos path is not configured - registering absolute repo path "%s"',
                absolute_repo_path)
            repo_config['path'] = str(absolute_repo_path)
            return

        try:
            repo_path = absolute_repo_path.relative_to(self.repos_path)
        except ValueError:
            _LOG.warning(
                'resolved repo path "%s" is not within configured repos path "%s"'
                ' - registering absolute path', absolute_repo_path, self.repos_path)
            repo_config['path'] = str(absolute_repo_path)
            return

        if str(repo_path) == repo_config['name']:
            del repo_config['path']
            _LOG.warning(
                'resolved repo path "%s" is within configured repos path "%s" and resolves'
                ' to the repository name "%s" - registering without redundant path data',
                absolute_repo_path, self.repos_path, repo_path)
            return

        repo_config['path'] = str(repo_path)
        _LOG.warning(
            'resolved repo path "%s" is within configured repos path "%s" - registering'
            ' relative path "%s"', absolute_repo_path, self.repos_path, repo_path)
