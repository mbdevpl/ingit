"""Boilerplate to handle local configuration.

Example usage:

from .config_boilerplate import initialize_config_directory

...

initialize_config_directory(app_name)
"""

import os
import pathlib
import platform
import typing as t

__updated__ = '2020-01-29'

CONFIG_PATHS = {
    'Linux': pathlib.Path('~', '.config'),
    'Darwin': pathlib.Path('~', 'Library', 'Preferences'),
    'Windows': pathlib.Path('%LOCALAPPDATA%')}

CONFIG_PATH = CONFIG_PATHS[platform.system()]


def normalize_path(path: t.Union[pathlib.Path, str]) -> t.Union[pathlib.Path, str]:
    if isinstance(path, str):
        return os.path.expanduser(os.path.expandvars(path))
    return pathlib.Path(normalize_path(str(path)))


def initialize_config_directory(app_name: str):
    """Create a configuration directory for an application."""
    config_path = normalize_path(CONFIG_PATH.joinpath(app_name))
    if not config_path.is_dir():
        config_path.mkdir(parents=True)
