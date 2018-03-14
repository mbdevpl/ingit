"""The ingit runtime."""

import collections
import functools
import logging
import pathlib
import platform
import re
import typing as t

import git
import ordered_set

from .runtime_interface import ask
from .json_config import \
    normalize_path, json_to_file, default_machine_configuration, acquire_configuration
from .repo_data import RepoData
from .project import Project

_LOG = logging.getLogger(__name__)


def regex_predicate(regex, name, tags, path, remotes):
    return (
        re.search(regex, name) is not None
        or any(re.search(regex, tag) is not None for tag in tags)
        or re.search(regex, str(path)) is not None
        or any(re.search(regex, name) for name, url in remotes.items()))


class Runtime:

    """The ingit runtime."""

    def __init__(self, runtime_config_path: pathlib.Path, repos_config_path: pathlib.Path,
                 hostname: str = None, interactive: t.Optional[bool] = None):
        self.runtime_config_path = runtime_config_path
        self.repos_config_path = repos_config_path
        self._hostname = platform.node() if hostname is None else hostname

        self.runtime_config = None
        self.repos_config = None
        self._machine_config = None
        self._interactive = interactive

        self.projects = None
        self._projects = []

        # prepare, possibly interactive

        self.runtime_config = acquire_configuration(self.runtime_config_path, 'runtime')
        self._machine_config = self._read_machine_config()
        # self.repos_path = pathlib.Path(normalize_path(self._machine_config['repos_path']))
        # self.interactive = self._machine_config['interactive']
        # if RuntimeInterfaceConfig.interactive is None:
        #    runtime_config['']

        self.repos_config = acquire_configuration(self.repos_config_path, 'repos')
        self.projects = self._read_projects()
        self._projects = [project for project in self.projects]

    @property
    def repos_path(self):
        return pathlib.Path(normalize_path(self._machine_config['repos_path']))

    @property
    def interactive(self):
        if self._interactive is None:
            return self._machine_config['interactive']
        return self._interactive

    def _read_machine_config(self):
        for machine in self.runtime_config['machines']:
            names = []
            if 'name' in machine:
                names.append(machine['name'])
            if 'names' in machine:
                names += machine['names']
            if '' in names or self._hostname in names:
                return machine

        ans = ask('No matching machine for "{}" found in configuration. Add it?'
                  .format(self._hostname))
        if ans != 'y':
            raise ValueError('No matching machine for "{}" found in configuration """{}"""'
                             .format(self._hostname, self.runtime_config))
        machine = self.register_machine(self._hostname)
        return machine

    def _read_projects(self) -> t.Sequence[Project]:
        """Get list of all projects in repositories configuration."""
        projects = []
        for repo in self.repos_config['repos']:
            name = repo['name']
            if 'path' in repo:
                path = pathlib.Path(normalize_path(repo['path']))
                if not path.is_absolute():
                    path = self.repos_path.joinpath(path)
            else:
                path = self.repos_path.joinpath(name)
            project = Project(name=name, tags=repo['tags'], path=path, remotes=repo['remotes'])
            projects.append(project)
        return projects

    def filter_projects(self, predicate: t.Union[collections.Callable, str]):
        """Select subset of all of the projects registered projects for processing."""
        assert isinstance(predicate, (collections.Callable, str)), type(predicate)
        if isinstance(predicate, str):
            predicate = functools.partial(regex_predicate, predicate)
        self._projects = [project for project in self.projects
                          if predicate(project.name, project.tags, project.path, project.remotes)]

    def execute(self, command: str, **command_options):
        """Execute the runtime."""
        command_executor = {
            'summary': self.execute_ingit_command,
            'register': self.execute_ingit_command,
            'clone': self.execute_git_command,
            'init': self.execute_git_command,
            'fetch': self.execute_git_command,
            'checkout': self.execute_git_command,
            'merge': self.execute_git_command,
            'push': self.execute_git_command,
            'gc': self.execute_git_command,
            'status': self.execute_git_command}[command]

        command_executor(command, **command_options)

    def execute_ingit_command(self, command, **command_options):
        command = {
            'summary': 'repositories_summary',
            'register': 'register_repository'}[command]
        implementation = getattr(self, command)
        implementation(**command_options)

    def execute_git_command(self, command: str, **command_options):
        command = {
            'gc': 'collect_garbage'}.get(command, command)
        for project in self._projects:
            implementation = getattr(project, command)
            implementation(**command_options)

    def repositories_summary(self):
        """Summarize registered repositories."""

        all_count = len(self._projects)
        was_filtered = all_count < len(self.repos_config['repos'])
        if was_filtered:
            print('Registered projects matching given conditions ({}):'.format(all_count))
        else:
            print('All registered projects ({}):'.format(all_count))
        initialised_count = 0
        project_paths_in_root = ordered_set.OrderedSet()
        for project in self._projects:
            if project.is_initialised:
                initialised_count += 1
            print(' -', project)
            try:
                project_paths_in_root.add(project.path.relative_to(self.repos_path))
            except:
                pass

        if initialised_count == all_count:
            print('all of them are initialised')
        else:
            print('{} of them are initialised ({} not)'
                  .format(initialised_count, all_count - initialised_count))

        non_repo_paths_in_root = ordered_set.OrderedSet()
        unregistered_in_root = ordered_set.OrderedSet()
        for path in self.repos_path.iterdir():
            if not path.is_dir():
                continue
            try:
                _ = git.Repo(str(path))
            except git.exc.InvalidGitRepositoryError:
                # TODO: recurse into non-git dir here
                non_repo_paths_in_root.add(path)
                continue
            relative_path = path.relative_to(self.repos_path)
            if relative_path in project_paths_in_root:
                continue
            unregistered_in_root.add(path)

        if unregistered_in_root:
            print('there are {} unregistered git repositories in configured repositories root "{}"'
                  .format(len(unregistered_in_root), self.repos_path))
            for path in unregistered_in_root:
                print(path)

        if non_repo_paths_in_root:
            print('there are {} not versioned folders in configured repositories root "{}"'
                  .format(len(non_repo_paths_in_root), self.repos_path))
            for path in non_repo_paths_in_root:
                print(path)

    def register_machine(self, name: str) -> dict:
        """Add machine to ingit runtime configuation."""
        assert isinstance(name, str), type(name)
        assert name
        for machine in self.runtime_config['machines']:
            names = []
            if 'name' in machine:
                names.append(machine['name'])
            if 'names' in machine:
                names += machine['names']
            if '' in names or name in names:
                raise ValueError('machine "{}" already in configuration'.format(name))
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
        _LOG.warning('registering repository: %s', repo_data)
        repo_config = repo_data.generate_repo_configuration()
        try:
            repo_config['path'] = str(pathlib.Path(repo_config['path']).resolve()
                                      .relative_to(self.repos_path))
        except ValueError:
            pass
        if repo_config['path'] == repo_config['name']:
            del repo_config['path']
        if tags is not None:
            repo_config['tags'] += tags
        _LOG.warning('adding repo to configuration: %s', repo_config)
        for project in self.projects:
            if project.name == repo_config['name']:
                raise ValueError('project named {} already exists in current configuration'
                                 .format(project.name))
        self.repos_config['repos'].append(repo_config)
        json_to_file(self.repos_config, self.repos_config_path)
