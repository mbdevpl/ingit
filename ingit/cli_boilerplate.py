"""Boilerplate useful when creating a command-line interface."""

import argparse
import logging
import sys
import textwrap
import typing as t

import argcomplete

from ._version import VERSION

__version__ = '2023.03.10'


class ArgumentDefaultsAndRawDescriptionHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Inherit from ArgumentDefaultsHelpFormatter and RawDescriptionHelpFormatter."""


def make_copyright_notice(
        year_from: int, year_to: t.Optional[int] = None, author: str = 'Mateusz Bysiek',
        license_name: str = 'Apache License 2.0', url: t.Optional[str] = None) -> str:
    """Assemble a copyright notice like "Copyright YYYY by Author(s). License Name. http://url/"."""
    if year_to is None or year_to == year_from:
        years = str(year_from)
    else:
        years = f'{year_from}-{year_to}'
    return f'Copyright {years} by {author}. {license_name}. {"" if url is None else url}'.rstrip()


def add_version_option(parser: argparse.ArgumentParser):
    """Add --version option to a given parser."""
    parser.add_argument(
        '--version', action='version', version=f'{parser.prog} {VERSION}, Python {sys.version}')


_LOGGING_LEVEL_MIN = logging.CRITICAL
_LOGGING_LEVEL_DEFAULT = logging.WARNING
_LOGGING_LEVEL_MAX = logging.DEBUG - 10


def verbosity_level_to_logging_level(verbosity: int) -> int:
    """Convert internal verbosity level to logging level from logging library."""
    return _LOGGING_LEVEL_MIN - verbosity * 10


def logging_level_to_verbosity_level(logging_level: int) -> int:
    """Convert logging level from logging library to internal verbosity level."""
    return (_LOGGING_LEVEL_MIN - logging_level) // 10


_VERBOSITY_MIN = logging_level_to_verbosity_level(_LOGGING_LEVEL_MIN)
_VERBOSITY_DEFAULT = logging_level_to_verbosity_level(_LOGGING_LEVEL_DEFAULT)
_VERBOSITY_MAX = logging_level_to_verbosity_level(_LOGGING_LEVEL_MAX)

_VERBOSE_MAX_COUNT = _VERBOSITY_MAX - _VERBOSITY_DEFAULT
_QUIET_MAX_COUNT = _VERBOSITY_DEFAULT - _VERBOSITY_MIN


def add_verbosity_group(parser: argparse.ArgumentParser) -> 'argparse._MutuallyExclusiveGroup':
    """Add parser option group for controlling application verbosity."""
    verbosity_group = parser.add_mutually_exclusive_group(required=False)
    verbosity_group.add_argument(
        '--verbose', '-v', action='count',
        help=f'''be more verbose than by default (repeat up to {_VERBOSE_MAX_COUNT} times
        for stronger effect)''')
    verbosity_group.add_argument(
        '--quiet', '-q', action='count',
        help=f'''be more quiet than by default (repeat up to {_QUIET_MAX_COUNT} times
        for stronger effect)''')
    verbosity_arg = verbosity_group.add_argument(
        '--verbosity', metavar='LEVEL', type=int, default=_VERBOSITY_DEFAULT,
        help=f'set verbosity level explicitly (normally from {_VERBOSITY_MIN} to {_VERBOSITY_MAX})')
    verbosity_arg.completer = argcomplete.completers.ChoicesCompleter(  # type: ignore
        choices=list(range(_VERBOSITY_MIN, _VERBOSITY_MAX)))
    return verbosity_group


def get_verbosity_level(parsed_args: argparse.Namespace) -> int:
    """Get verbosity level from parsed arguments after using add_verbosity_group() on a parser."""
    level = parsed_args.verbosity
    if parsed_args.verbose is not None:
        if parsed_args.verbose > _VERBOSE_MAX_COUNT:
            raise ValueError('too many repetitions of --verbose/-v')
        level += parsed_args.verbose
    if parsed_args.quiet is not None:
        if parsed_args.quiet > _QUIET_MAX_COUNT:
            raise ValueError('too many repetitions of --quiet/-q')
        level -= parsed_args.quiet
    return level


def get_logging_level(parsed_args: argparse.Namespace) -> int:
    """Get logging level equivalent to the verbosity from parsed arguments.

    This function only works after using add_verbosity_group().
    """
    return verbosity_level_to_logging_level(get_verbosity_level(parsed_args))


def dedent_except_first_line(text: str) -> str:
    """Dedent all lines of text except the 1st, using textwrap.dedent()."""
    try:
        newline = text.index('\n') + 1
    except ValueError:
        return text
    return text[:newline] + textwrap.dedent(text[newline:])
