"""Boilerplate useful to setup logging.

To reduce boilerplate necessary to setup logging for your application, first
create a file _logging.py with contents as below:

"" "Logging configuration." ""

from . import logging_boilerplate


class Logging(logging_boilerplate.Logging):
    "" "Logging configuration." ""

    directory = ''

You can and should adjust the class fields to your needs, please take a look at the Logging class
implementation for details.

Then, add the following to your __init__.py, or somewhere else you want:

from ._logging import Logging

Logging.configure()
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

__version__ = '2022.08.15'

LOGS_PATHS = {
    'Linux': pathlib.Path('~', '.local', 'share'),
    'Darwin': pathlib.Path('~', 'Library', 'Logs'),
    'Windows': pathlib.Path('%LOCALAPPDATA%')}

LOGS_PATH = LOGS_PATHS[platform.system()]

# _LOG.setLevel(_LOG_LEVEL)
# _LOG.log(_LOG_LEVEL, '%s logger level set to %s', __name__, logging.getLevelName(_LOG_LEVEL))

DEFAULT_LOGGING_LEVEL_GLOBAL = logging.NOTSET
DEFAULT_LOGGING_LEVEL_PACKAGE = logging.DEBUG
DEFAULT_LOGGING_LEVEL_TEST = logging.DEBUG
DEFAULT_LOGGING_LEVEL_OTHER = logging.WARNING
DEFAULT_LEVEL = logging.DEBUG

LEVEL_ENVVAR_NAME = 'LOGGING_LEVEL'

DATETIME_FORMAT_DAILY = r'%Y%m%d'
DATETIME_FORMAT_PRECISE = r'%Y%m%d-%H%M%S'

LOG_FORMAT_BRIEF = r'{name} [{levelname}] {message}'
LOG_FORMAT_BRIEF_COLOURED = r'{name} [{log_color}{levelname}{reset}] {message}'
LOG_FORMAT_PRECISE = f'{{asctime}} {LOG_FORMAT_BRIEF}'
LOG_FORMAT_PRECISE_COLOURED = f'{{asctime}} {LOG_FORMAT_BRIEF_COLOURED}'


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
    timestamp = datetime.datetime.now().strftime(DATETIME_FORMAT_DAILY)
    return f'{app_name}_{timestamp}.log'


def log_filename_precise(app_name: str) -> str:
    timestamp = datetime.datetime.now().strftime(DATETIME_FORMAT_PRECISE)
    return f'{app_name}_{timestamp}.log'


class Logging:
    """Boilerplate to configure logging for an application."""

    packages: t.List[str]

    directory: str
    filename: t.Optional[str] = None

    enable_console: bool = True
    enable_file: bool = False

    level_global: int = DEFAULT_LOGGING_LEVEL_GLOBAL
    """Global logging cut-off filter.

    If set higher than any other level_* fields, it overrides then and filters all messages
    below the level.

    If set lower than some of other level_* fields, the values of respective fields still apply.
    """

    level_package: int = DEFAULT_LOGGING_LEVEL_PACKAGE
    """Logging level for in-package logging.

    This applies to the packages in the packages field.
    """

    level_test: int = DEFAULT_LOGGING_LEVEL_TEST
    """Logging level"""

    level_other: int = DEFAULT_LOGGING_LEVEL_OTHER

    @property
    @classmethod
    def _absolute_path(cls) -> pathlib.Path:
        assert cls.directory is not None
        filename = log_filename_precise(cls.directory) if cls.filename is None else cls.filename
        return normalize_path(LOGS_PATH.joinpath(cls.directory, filename))

    @classmethod
    def _create_logs_folder(cls):
        assert cls.directory is not None
        logs_path = normalize_path(LOGS_PATH.joinpath(cls.directory))
        if not logs_path.is_dir():
            logs_path.mkdir(parents=True)

    @classmethod
    def configure_basic(cls):
        """Configure basic logging for an application.

        Basic logging is logging to the console with colored logging, or logging to a single file.
        """
        if cls.enable_console:
            assert not cls.enable_file
            cls._configure_basic_console()
        elif cls.enable_file:
            cls._create_logs_folder()
            logging.basicConfig(
                level=logging_level_from_envvar(LEVEL_ENVVAR_NAME, default=DEFAULT_LEVEL),
                filename=str(cls._absolute_path))
        else:
            logging.basicConfig(
                level=logging_level_from_envvar(LEVEL_ENVVAR_NAME, default=DEFAULT_LEVEL))

        logging.getLogger().setLevel(cls.level_other)
        for package in cls.packages:
            logging.getLogger(package).setLevel(cls.level_package)
        logging.getLogger('test').setLevel(cls.level_test)

    @classmethod
    def _configure_basic_console(cls):
        """Configure basic logging to the console with colored logging."""
        handler = logging.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(LOG_FORMAT_BRIEF_COLOURED, style='{'))

        logging.basicConfig(
            level=logging_level_from_envvar(LEVEL_ENVVAR_NAME, default=DEFAULT_LEVEL),
            handlers=[handler])

    @classmethod
    def configure(cls):
        """Configure logging for an application."""
        logging_config = {
            'formatters': {
                'brief': {
                    '()': 'colorlog.ColoredFormatter',
                    'style': '{',
                    'format': LOG_FORMAT_BRIEF_COLOURED},
                'precise': {
                    'style': '{',
                    'format': LOG_FORMAT_PRECISE}},
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
            cls._create_logs_folder()
            logging_config['handlers']['file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'precise',
                'level': logging.NOTSET,
                'filename': str(cls._absolute_path),
                'maxBytes': 1 * 1024 * 1024,
                'backupCount': 10}
            logging_config['root']['handlers'].append('file')
        logging.config.dictConfig(logging_config)

    @classmethod
    def configure_from_json(cls):
        raise NotImplementedError()


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
    Given a called_function, convert write(text) calls to called_function(text) calls.
    For example: StreamToCall(logging.warning) will redirect all writes to logging.warning().
    """

    def __init__(self, called_function: collections.abc.Callable):
        assert callable(called_function), type(called_function)
        self._function = called_function

    def write(self, message: str, *args):
        """Redirect the write to the logging function."""
        while message.endswith('\r') or message.endswith('\n'):
            message = message[:-1]
        self._function(message, *args)

    def flush(self):
        """Flush can be a no-op."""
