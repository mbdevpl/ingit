"""The ingit runtime."""

import collections
import logging
import os
import pathlib
import platform
import tempfile
import typing as t

from .project import Project

_LOG = logging.getLogger(__name__)


def run(runtime_config: dict, repos_config: dict, predicate: collections.Callable,
        command: str, **command_options):
    """Run the runtime."""
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
            repos_path_str = os.path.expandvars(machine['repos_path'])
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
