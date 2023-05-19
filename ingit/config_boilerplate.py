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

__version__ = '2023.04.08'

CONFIG_PATHS = {
    'Linux': pathlib.Path('~', '.config'),
    'Darwin': pathlib.Path('~', 'Library', 'Preferences'),
    'Windows': pathlib.Path('%LOCALAPPDATA%')}

CONFIG_PATH = CONFIG_PATHS[platform.system()]

PathOrStr = t.TypeVar('PathOrStr', pathlib.Path, str)


def normalize_path(path: PathOrStr) -> PathOrStr:
    """Normalize path variable by expanding user symbol and environment variables."""
    if isinstance(path, str):
        return os.path.expanduser(os.path.expandvars(path))
    assert isinstance(path, pathlib.Path), type(path)
    _ = normalize_path(str(path))
    return pathlib.Path(_)


def initialize_config_directory(app_name: str):
    """Create a configuration directory for an application."""
    config_path = normalize_path(CONFIG_PATH.joinpath(app_name))
    if not config_path.is_dir():
        config_path.mkdir(parents=True)
