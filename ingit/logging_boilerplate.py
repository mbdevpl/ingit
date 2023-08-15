"""Boilerplate useful to setup logging.

To reduce boilerplate necessary to setup logging for your application, first
create a file _logging.py with contents as below:

"" "Logging configuration." ""

from . import logging_boilerplate


class Logging(logging_boilerplate.Logging):
    "" "Logging configuration." ""

    packages = ['package_name']


More advanced usage could be:

"" "Logging configuration." ""

import logging

from . import logging_boilerplate


class Logging(logging_boilerplate.Logging):
    "" "Logging configuration." ""

    packages = ['package_name']
    level_package = logging.INFO
    enable_file = True
    directory = 'package_name'


You can and should adjust the class fields to your needs, please take a look at the Logging class
implementation for details.

Then, add the following to your __main__.py, or somewhere else you want:

from ._logging import Logging


if __name__ == '__main__':
    Logging.configure()
    ...


As for using the logging in your code, you can use it as usual, for example:

# in a standalone script:
_LOG = logging.getLogger(pathlib.Path(__file__).stem)
# in a standalone script that can also be imported:
_LOG = logging.getLogger(pathlib.Path(__file__).stem if __name__ == '__main__' else __name__)
# in __main__.py:
_LOG = logging.getLogger(pathlib.Path(__file__).parent.name)
# in usual module files:
_LOG = logging.getLogger(__name__)
"""

import collections.abc
import datetime
import logging
import logging.config
import os
import pathlib
import platform
import typing as t

from boilerplates.config import normalize_path
import colorlog

__version__ = '2023.05.20'

LOGS_PATHS = {
    'Linux': pathlib.Path('~', '.local', 'share'),
    'Darwin': pathlib.Path('~', 'Library', 'Logs'),
    'Windows': pathlib.Path('%LOCALAPPDATA%')}

LOGS_PATH = LOGS_PATHS[platform.system()]

DEFAULT_LOGGING_LEVEL_GLOBAL = logging.DEBUG
DEFAULT_LOGGING_LEVEL_PACKAGE = logging.DEBUG
DEFAULT_LOGGING_LEVEL_TEST = logging.DEBUG
DEFAULT_LOGGING_LEVEL_OTHER = logging.WARNING

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
    """List of packages that are considered in-package/local/internal."""

    directory: str
    """This must be set if enable_file is True."""

    filename: t.Optional[str] = None
    """Choose a custom log filename, instead of an auto-generated one."""

    enable_console: bool = True
    """Default True, you can disable console logging by setting this to False."""

    enable_file: bool = False
    """Default False, you can enable file logging by setting this to True."""

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
    """Logging level for tests.

    This applies to packages with name basically starting with 'test.*'.
    """

    level_other: int = DEFAULT_LOGGING_LEVEL_OTHER
    """Logging level for all other packages.

    This applies to the root logger, so to all packages not covered by level_package and level_test.
    """

    @classmethod
    def _log_absolute_path(cls) -> pathlib.Path:
        assert cls.directory is not None
        filename = log_filename_precise(cls.directory) if cls.filename is None else cls.filename
        return normalize_path(LOGS_PATH.joinpath(cls.directory, filename))

    @classmethod
    def _create_logs_folder(cls):
        assert cls.directory is not None
        logs_path = normalize_path(LOGS_PATH.joinpath(cls.directory))
        assert logs_path.parent.exists(), logs_path.parent
        logs_path.mkdir(parents=False, exist_ok=True)

    @classmethod
    def _set_default_logging_levels(cls):
        logging.getLogger().setLevel(cls.level_other)
        for package in getattr(cls, 'packages', []):
            logging.getLogger(package).setLevel(cls.level_package)
        logging.getLogger('test').setLevel(cls.level_test)

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
                level=logging_level_from_envvar(LEVEL_ENVVAR_NAME, default=cls.level_global),
                filename=str(cls._log_absolute_path()))
        else:
            logging.basicConfig(
                level=logging_level_from_envvar(LEVEL_ENVVAR_NAME, default=cls.level_global))

        cls._set_default_logging_levels()

    @classmethod
    def _configure_basic_console(cls):
        """Configure basic logging to the console with colored logging."""
        handler = logging.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(LOG_FORMAT_BRIEF_COLOURED, style='{'))

        logging.basicConfig(
            level=logging_level_from_envvar(LEVEL_ENVVAR_NAME, default=cls.level_global),
            handlers=[handler])

    @classmethod
    def configure(cls):
        """Configure logging for an application."""
        logging_config = {
            'formatters': {
                'console': {
                    '()': 'colorlog.ColoredFormatter',
                    'style': '{',
                    'format': LOG_FORMAT_PRECISE_COLOURED},
                'file': {
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
                'formatter': 'console',
                'level': logging_level_from_envvar(LEVEL_ENVVAR_NAME, default=cls.level_global),
                'stream': 'ext://sys.stdout'}
            logging_config['root']['handlers'].append('console')
        if cls.enable_file:
            cls._create_logs_folder()
            logging_config['handlers']['file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'file',
                'level': logging.NOTSET,
                'filename': str(cls._log_absolute_path()),
                'maxBytes': 1 * 1024 * 1024,
                'backupCount': 10}
            logging_config['root']['handlers'].append('file')
        logging.config.dictConfig(logging_config)

        cls._set_default_logging_levels()


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
