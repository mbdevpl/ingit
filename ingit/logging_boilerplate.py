"""Boilerplate useful to setup logging.

To reduce boilerplate necessary to setup logging for your application, first
create a file _logging.py with contents as shown in SETUP_TEMPLATE.

Then, add the following to your __init__.py, or somewhere else you want:

""
from ._logging import Logging

Logging.configure()
""

"" "Logging configuration." ""

import logging_boilerplate


class Logging(logging_boilerplate.Logging):
    "" "Logging configuration." ""

    directory = ''
"""

import collections.abc
import datetime
import logging
import logging.config
import os
import pathlib
import platform
import typing as t

import colorlog

from .config_boilerplate import normalize_path

__version__ = '2022.01.03'

LOGS_PATHS = {
    'Linux': pathlib.Path('~', '.local', 'share'),
    'Darwin': pathlib.Path('~', 'Library', 'Logs'),
    'Windows': pathlib.Path('%LOCALAPPDATA%')}

LOGS_PATH = LOGS_PATHS[platform.system()]

'''
logging.basicConfig()

logging.basicConfig(level=logging.INFO)
# logging.getLogger('music_metadata_sync').setLevel(logging.WARNING)

logging.basicConfig(
    level=getattr(logging, os.environ.get('LOGGING_LEVEL', 'warning').upper(), logging.WARNING))

_HANDLER = logging.StreamHandler()
_HANDLER.setFormatter(colorlog.ColoredFormatter(
    '{name} [{log_color}{levelname}{reset}] {message}', style='{'))
logging.basicConfig(level=logging.INFO, handlers=[_HANDLER])

_LOG = logging.getLogger(__name__)
_LOG_LEVEL = logging.INFO

_LOG.setLevel(_LOG_LEVEL)
_LOG.log(_LOG_LEVEL, '%s logger level set to %s', __name__, logging.getLevelName(_LOG_LEVEL))
'''

DEFAULT_LEVEL = logging.WARNING
LEVEL_ENVVAR_NAME = 'LOGGING_LEVEL'


def logging_level_from_envvar(envvar: str, default: int = logging.WARNING) -> int:
    """Translate text envvar value into an integer corresponding to a logging level."""
    envvar_value = os.environ.get(envvar)
    if envvar_value is None:
        return default
    envvar_value = envvar_value.upper()
    if not hasattr(logging, envvar_value):
        try:
            return int(envvar_value)
        except ValueError:
            return default
    return getattr(logging, envvar_value)


def log_filename_basic(app_name: str) -> str:
    return f'{app_name}.log'


def log_filename_daily(app_name: str) -> str:
    _ = datetime.datetime.now().strftime(r'%Y%m%d')
    return f'{app_name}-{_}.log'


def log_filename_precise(app_name: str) -> str:
    _ = datetime.datetime.now().strftime(r'%Y%m%d-%H%M%S')
    return f'{app_name}-{_}.log'


class Logging:
    """Boilerplate to configure logging for an application."""

    directory: str
    filename = None  # type: str

    enable_console = True  # type: bool
    enable_file = False  # type: bool
    level = None  # type: int

    # @classmethod
    # def configure_basic(cls):
    #     logging.basicConfig(
    #         level=logging_level_from_envvar(LEVEL_ENVVAR_NAME, default=DEFAULT_LEVEL),
    #         filename=normalize_path(str(LOGS_PATH.joinpath(cls.directory, cls.filename))))

    @classmethod
    def configure(cls):
        assert cls.directory is not None
        logs_path = normalize_path(LOGS_PATH.joinpath(cls.directory))
        if not logs_path.is_dir():
            logs_path.mkdir(parents=True)
        logging_config = {
            'formatters': {
                'brief': {
                    '()': 'colorlog.ColoredFormatter',
                    'style': '{',
                    'format': '{name} [{log_color}{levelname}{reset}] {message}'},
                'precise': {
                    'style': '{',
                    'format': '{asctime} {name} [{levelname}] {message}'}},
            'handlers': {},
            'root': {
                'handlers': [],
                'level': logging.NOTSET},
            'version': 1,
            'disable_existing_loggers': False}
        if cls.enable_console:
            logging_config['handlers']['console'] = {
                'class': 'logging.StreamHandler',
                'formatter': 'brief',
                'level': logging_level_from_envvar(LEVEL_ENVVAR_NAME, default=DEFAULT_LEVEL),
                'stream': 'ext://sys.stdout'}
            logging_config['root']['handlers'].append('console')
        if cls.enable_file:
            filename = log_filename_precise(cls.directory) if cls.filename is None else cls.filename
            logging_config['handlers']['file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'precise',
                'level': logging.NOTSET,
                'filename': str(logs_path.joinpath(filename)),
                'maxBytes': 1 * 1024 * 1024,
                'backupCount': 10}
            logging_config['root']['handlers'].append('console')
        logging.config.dictConfig(logging_config)

    @classmethod
    def configure_from_json(cls):
        pass


def unittest_verbosity() -> t.Optional[int]:
    """Retrieve the verbosity setting of the currently running unittest program.

    Return None if currently running program is not unittest.

    Default verbosity level is 1, 0 means quiet and 2 means verbose.
    """
    import inspect  # pylint: disable=import-outside-toplevel
    import unittest  # pylint: disable=import-outside-toplevel

    frame = inspect.currentframe()
    while frame:
        self_ = frame.f_locals.get('self')
        if isinstance(self_, unittest.TestProgram):
            return self_.verbosity
        frame = frame.f_back
    return None


class StreamToCall:
    """Redirect stream writes to a function call.

    Enable using logging instances as a file-like objects.
    Given a logging_function, convert write(text) calls to logging_function(text) calls.
    For example: StreamToLog(logging.warning) will redirect all writes to logging.warning().
    """

    def __init__(self, logging_function: collections.abc.Callable):
        assert callable(logging_function)
        self.logging_function = logging_function

    def write(self, message: str, *args):
        """Redirect the write to the logging function."""
        while message.endswith('\r') or message.endswith('\n'):
            message = message[:-1]
        self.logging_function(message, *args)

    def flush(self):
        """Flush can be a no-op."""
