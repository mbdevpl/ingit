"""The ingit runtime."""

import collections
import logging
import os
import pathlib
import platform
import tempfile
import typing as t

import git

from ._version import VERSION
from .runtime_interface import ask
from .json_config import normalize_path, json_to_file, file_to_json
from .repo_data import RepoData
from .project import Project

_LOG = logging.getLogger(__name__)


def default_runtime_configuration():
    return {
        'description': 'ingit runtime configuration file',
        'ingit-version': VERSION,
        'machines': [
            {'name': platform.node(), 'repos_path': os.environ['HOME']}]}


def acquire_runtime_configuration(path: pathlib.Path):
    path = normalize_path(path)
    try:
        return file_to_json(path)
    except FileNotFoundError as err:
        ans = ask('Runtime configuration file {} does not exist. Create a default one?'
                  .format(path))
        if ans != 'y':
            raise err
        json_to_file(default_runtime_configuration(), path)
    return file_to_json(path)


def default_repos_configuration():
    return {
        'description': 'ingit repositories configuration file',
        'ingit-version': VERSION,
        'repos': []}


def acquire_repos_configuration(path: pathlib.Path):
    path = normalize_path(path)
    try:
        return file_to_json(path)
    except FileNotFoundError as err:
        ans = ask('Repositories configuration file {} does not exist. Create a default one?'
                  .format(path))
        if ans != 'y':
            raise err
        json_to_file(default_repos_configuration(), path)
    return file_to_json(path)


def run(runtime_config_path: pathlib.Path, repos_config_path: pathlib.Path,
        predicate: collections.Callable, command: str, **command_options):
    """Run the runtime."""
    runtime_config = acquire_runtime_configuration(runtime_config_path)
    repos_config = acquire_repos_configuration(repos_config_path)
    if command == 'register':
        register_repository(repos_config, **command_options)
        json_to_file(repos_config, repos_config_path)
        return
    projects = resolve_configs(runtime_config, repos_config, predicate)
    for project in projects:
        implementation = getattr(project, command)
        implementation(**command_options)


def resolve_configs(runtime_config, repos_config, predicate=None) -> t.List[Project]:
    """Use raw JSON configuration dictionaries and a predicate to form list of projects."""
    runtime_data = resolve_runtime_config(runtime_config)
    projects = resolve_repos_config(repos_config, *runtime_data)
    if predicate is None:
        return projects
    return filter_projects(projects, predicate)


def resolve_runtime_config(runtime_config):
    """Resolve raw JSON of runtime configuration."""
    hostname = platform.node()
    repos_path = None
    for machine in runtime_config['machines']:
        names = []
        repos_path = None
        if 'name' in machine:
            names.append(machine['name'])
        if 'names' in machine:
            names += machine['names']
        if '' in names or hostname in names:
            repos_path_str = normalize_path(machine['repos_path'])
            if repos_path_str == 'tempfile.gettempdir()':
                repos_path_str = tempfile.gettempdir()
            repos_path = pathlib.Path(repos_path_str).resolve()
            break

    if repos_path is None:
        raise ValueError('no matching machine for "{}" found in configuration: """{}"""'
                         .format(hostname, runtime_config))

    return hostname, names, repos_path


def resolve_repos_config(repos_config, hostname, names, repos_path: pathlib.Path):
    projects = []
    for repo in repos_config['repos']:
        name = repo['name']
        path = repo['path'] if 'path' in repo else repos_path.joinpath(name)
        project = Project(name=name, tags=repo['tags'], path=path, remotes=repo['remotes'])
        projects.append(project)
    return projects


def filter_projects(projects, predicate):
    filtered_projects = [project for project in projects
                         if predicate(project.name, project.tags, project.path, project.remotes)]
    return filtered_projects


def register_repository(repos_config, tags: t.Sequence[str], path: pathlib.Path):
    repo = git.Repo(str(path))
    repo_data = RepoData(repo)
    _LOG.warning('registering repository: %s', repo_data)
    repo_config = repo_data.generate_repo_configuration()
    repo_config['tags'] += tags
    _LOG.warning('adding to configuration: %s', repo_config)
    repos_config['repos'].append(repo_config)
