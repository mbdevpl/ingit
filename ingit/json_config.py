"""JSON-based configuration I/O."""

import json
import json.decoder
import logging
import pathlib
import platform

from boilerplates.config import CONFIGS_PATH, normalize_path

from ._version import VERSION
from .runtime_interface import ask

_LOG = logging.getLogger(__name__)

JSON_INDENT = 2

JSON_ENSURE_ASCII = False

_CONFIG_DIRECTORY = CONFIGS_PATH.joinpath('ingit')
REPO_LISTS_DIRECTORY = _CONFIG_DIRECTORY.joinpath('repos.d')
RUNTIME_CONFIG_PATH = _CONFIG_DIRECTORY.joinpath('ingit_config.json')
DEFAULT_REPOS_CONFIG_PATH = _CONFIG_DIRECTORY.joinpath('ingit_repos.json')


def json_to_str(data: dict) -> str:
    assert isinstance(data, dict), type(data)
    return json.dumps(data, indent=JSON_INDENT, ensure_ascii=JSON_ENSURE_ASCII)


def str_to_json(text: str) -> dict:
    """Convert JSON string into an object."""
    try:
        return json.loads(text)
    except json.decoder.JSONDecodeError as err:
        lines = text.splitlines(keepends=True)
        raise ValueError(
            f'\n{"".join(lines[max(0, err.lineno - 10):err.lineno])}{"-" * err.colno}'
            f'\n{"".join(lines[err.lineno:min(err.lineno + 10, len(lines))])}') from err


def json_to_file(data: dict, path: pathlib.Path) -> None:
    """Save JSON object to a file."""
    assert isinstance(data, dict), type(data)
    assert isinstance(path, pathlib.Path), type(path)
    text = json_to_str(data)
    with normalize_path(path).open('w', encoding='utf-8') as json_file:
        json_file.write(text)
        json_file.write('\n')


def file_to_json(path: pathlib.Path) -> dict:
    """Create JSON object from a file."""
    assert isinstance(path, pathlib.Path), type(path)
    with normalize_path(path).open('r', encoding='utf-8') as json_file:
        text = json_file.read()
    try:
        data = str_to_json(text)
    except ValueError as err:
        raise ValueError(f'in file "{path}"') from err
    return data


def default_runtime_configuration():
    return {
        'description': 'ingit runtime configuration file',
        'ingit-version': VERSION,
        'machines': [default_machine_configuration()]}


def default_machine_configuration(name=None):
    return {'interactive': True,
            'name': platform.node() if name is None else name,
            'repos_path': '~'}


def default_repos_configuration():
    return {
        'description': 'ingit repositories configuration file',
        'ingit-version': VERSION,
        'repos': []}


CONFIG_TYPES = {
    'runtime': (default_runtime_configuration, 'Runtime'),
    'repos': (default_repos_configuration, 'Repositories')}


def acquire_configuration(path: pathlib.Path, config_type: str):
    """Read (or create default) and return ingit configuration."""
    default_generator, config_type_name = CONFIG_TYPES[config_type]
    path = normalize_path(path)
    try:
        return file_to_json(path)
    except FileNotFoundError as err:
        ans = ask(f'{config_type_name} configuration file {path} does not exist.'
                  ' Create a default one?')
        if ans != 'y':
            raise err
        path.parent.mkdir(parents=True, exist_ok=True)
        config = default_generator()
        json_to_file(config, path)
        return config
    return file_to_json(path)


def acquire_repos_configuration(path: pathlib.Path):
    """Read (or create default) and return ingit repositories configuration."""
    if path != DEFAULT_REPOS_CONFIG_PATH:
        return acquire_configuration(path, 'repos')
    incremental_config = default_repos_configuration()
    repo_lists_directory = normalize_path(REPO_LISTS_DIRECTORY)
    if repo_lists_directory.is_dir():
        _LOG.warning('loading repository lists from %s', repo_lists_directory)
        for path in repo_lists_directory.iterdir():
            if path.suffix != '.json':
                continue
            _LOG.warning('reading repos from %s', path)
            incremental_config['repos'] += file_to_json(path)['repos']
    if normalize_path(DEFAULT_REPOS_CONFIG_PATH).exists():
        incremental_config['repos'] += \
            acquire_configuration(DEFAULT_REPOS_CONFIG_PATH, 'repos')['repos']
    return incremental_config
