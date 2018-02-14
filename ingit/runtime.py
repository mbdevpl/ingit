"""The ingit runtime."""

import collections
import functools
import logging
import pathlib
import platform
import re
import typing as t

import git

from ._version import VERSION
from .runtime_interface import ask
from .json_config import normalize_path, json_to_file, file_to_json
from .repo_data import RepoData
from .project import Project

_LOG = logging.getLogger(__name__)

CONFIG_DIRECTORIES = {
    'Linux': pathlib.Path('~', '.config', 'ingit'),
    'Darwin': pathlib.Path('~', 'Library', 'Preferences', 'ingit'),
    'Windows': pathlib.Path('%LOCALAPPDATA%', 'ingit')}

CONFIG_DIRECTORY = CONFIG_DIRECTORIES[platform.system()]
RUNTIME_CONFIG_PATH = pathlib.Path(CONFIG_DIRECTORY, 'ingit_config.json')
REPOS_CONFIG_PATH = pathlib.Path(CONFIG_DIRECTORY, 'ingit_repos.json')


def default_runtime_configuration():
    return {
        'description': 'ingit runtime configuration file',
        'ingit-version': VERSION,
        'machines': [
            {'name': platform.node(), 'repos_path': '~'}]}


def acquire_runtime_configuration(path: pathlib.Path):
    """Read (or create default) and return ingit runtime configuration."""
    path = normalize_path(path)
    try:
        return file_to_json(path)
    except FileNotFoundError as err:
        ans = ask('Runtime configuration file {} does not exist. Create a default one?'
                  .format(path))
        if ans != 'y':
            raise err
        path.parent.mkdir(parents=True, exist_ok=True)
        json_to_file(default_runtime_configuration(), path)
    return file_to_json(path)


def default_repos_configuration():
    return {
        'description': 'ingit repositories configuration file',
        'ingit-version': VERSION,
        'repos': []}


def acquire_repos_configuration(path: pathlib.Path):
    """Read (or create default) and return ingit repositories configuration."""
    path = normalize_path(path)
    try:
        return file_to_json(path)
    except FileNotFoundError as err:
        ans = ask('Repositories configuration file {} does not exist. Create a default one?'
                  .format(path))
        if ans != 'y':
            raise err
        path.parent.mkdir(parents=True, exist_ok=True)
        json_to_file(default_repos_configuration(), path)
    return file_to_json(path)


def regex_predicate(regex, name, tags, path, remotes):
    return (
        re.search(regex, name) is not None
        or any(re.search(regex, tag) is not None for tag in tags)
        or re.search(regex, str(path)) is not None
        or any(re.search(regex, name) for name, url in remotes.items()))


def run(runtime_config_path: pathlib.Path, repos_config_path: pathlib.Path,
        predicate: collections.Callable, regex: str, command: str, **command_options):
    """Run the runtime."""
    runtime_config = acquire_runtime_configuration(runtime_config_path)
    repos_path, found = resolve_runtime_config(runtime_config)
    if not found:
        json_to_file(runtime_config, runtime_config_path)
    repos_config = acquire_repos_configuration(repos_config_path)
    projects = resolve_repos_config(repos_config, repos_path)
    if command == 'register':
        register_repository(repos_path, repos_config, projects, **command_options)
        json_to_file(repos_config, repos_config_path)
        return
    if predicate is not None:
        projects = filter_projects(projects, predicate)
    if regex is not None:
        projects = filter_projects(projects, functools.partial(regex_predicate, regex))
    if command == 'gc':
        command = 'collect_garbage'
    for project in projects:
        implementation = getattr(project, command)
        implementation(**command_options)


def find_repos_path(runtime_config: dict, hostname: str) -> t.Optional[str]:
    for machine in runtime_config['machines']:
        names = []
        if 'name' in machine:
            names.append(machine['name'])
        if 'names' in machine:
            names += machine['names']
        if '' in names or hostname in names:
            repos_path_str = normalize_path(machine['repos_path'])
            return pathlib.Path(repos_path_str)
    return None


def resolve_runtime_config(runtime_config: dict) -> str:
    """Resolve raw JSON of runtime configuration."""
    hostname = platform.node()
    repos_path = find_repos_path(runtime_config, hostname)

    if repos_path is not None:
        return repos_path, True

    ans = ask('No matching machine for "{}" found in configuration. Add it?'.format(hostname))
    if ans != 'y':
        raise ValueError('No matching machine for "{}" found in configuration """{}"""'
                         .format(hostname, runtime_config))
    repos_path = pathlib.Path('~')
    register_machine(runtime_config, hostname, repos_path)
    return repos_path, False


def resolve_repos_config(repos_config: dict, repos_path: pathlib.Path):
    projects = []
    for repo in repos_config['repos']:
        name = repo['name']
        if 'path' in repo:
            path = pathlib.Path(repo['path'])
            try:
                path = path.relative_to(repos_path)
            except ValueError:
                pass
        else:
            path = repos_path.joinpath(name)
        project = Project(name=name, tags=repo['tags'], path=path, remotes=repo['remotes'])
        projects.append(project)
    return projects


def filter_projects(projects: t.Sequence[Project], predicate):
    filtered_projects = [project for project in projects
                         if predicate(project.name, project.tags, project.path, project.remotes)]
    return filtered_projects


def register_machine(runtime_config, name: str, repos_path: pathlib.Path):
    machine_config = {'name': name, 'repos_path': str(repos_path)}
    _LOG.warning('adding machine to configuration: %s', machine_config)
    runtime_config['machines'].append(machine_config)


def register_repository(repos_path: pathlib.Path, repos_config: dict, projects: t.Sequence[Project],
                        tags: t.Sequence[str], path: pathlib.Path):
    """Add repo to ingit repositories configuration."""
    repo = git.Repo(str(path))
    repo_data = RepoData(repo)
    _LOG.warning('registering repository: %s', repo_data)
    repo_config = repo_data.generate_repo_configuration()
    try:
        repo_config['path'] = str(pathlib.Path(repo_config['path']).relative_to(repos_path))
    except ValueError:
        pass
    if repo_config['path'] == repo_config['name']:
        del repo_config['path']
    if tags is not None:
        repo_config['tags'] += tags
    _LOG.warning('adding repo to configuration: %s', repo_config)
    for project in projects:
        if project.name == repo_config['name']:
            raise ValueError('project named {} already exists in current configuration'
                             .format(project.name))
    repos_config['repos'].append(repo_config)
