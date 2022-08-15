"""Boilerplate useful when creating a command-line interface."""

import argparse
import logging
import sys
import textwrap
import typing as t

import argcomplete

from ._version import VERSION

__version__ = '2022.01.03'

VERBOSITY_DEFAULT = (logging.CRITICAL - logging.WARNING) // 10  # integer from 0 to 5


class ArgumentDefaultsAndRawDescriptionHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Inherit from ArgumentDefaultsHelpFormatter and RawDescriptionHelpFormatter."""


def make_copyright_notice(
        year_from: int, year_to: t.Optional[int] = None, author: str = 'Mateusz Bysiek',
        license_name: str = 'Apache License 2.0', url: t.Optional[str] = None):
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


def add_verbosity_group(parser: argparse.ArgumentParser) -> 'argparse._MutuallyExclusiveGroup':
    """Add parser option group for controlling application verbosity."""
    verbosity_group = parser.add_mutually_exclusive_group(required=False)
    verbosity_group.add_argument(
        '--verbose', '-v', action='count',
        help='be more verbose than by default (repeat up to 2 times for stronger effect)')
    verbosity_group.add_argument(
        '--quiet', '-q', action='count',
        help='be more quiet than by default (repeat up to 3 times for stronger effect)')
    verbosity_group.add_argument(
        '--verbosity', metavar='LEVEL', type=int, default=VERBOSITY_DEFAULT,
        help=f'set verbosity level explicitly (normally from {0} to {5})') \
        .completer = argcomplete.completers.ChoicesCompleter(choices=list(range(0, 5 + 1, 1)))
    return verbosity_group


def __(parser):
    parser.add_argument(
        '--quiet', '-q', action='store_true', default=False, required=False,
        help='''do not output anything but critical errors; overrides "--verbose" and "--debug"
        if present; sets logging level to CRITICAL''')

    parser.add_argument(
        '--verbose', '-v', action='store_true', default=False, required=False,
        help='''output non-critical information; sets logging level to INFO''')

    parser.add_argument(
        '--debug', action='store_true', default=False, required=False,
        help='''output information at debugging level; overrides "--verbose" if present; sets
        logging level to DEBUG''')


def get_verbosity_level(parsed_args: argparse.Namespace) -> int:
    """Use to get verbosity level after using add_verbosity_group()."""
    level = parsed_args.verbosity
    if parsed_args.verbose is not None:
        level -= parsed_args.verbose
    if parsed_args.quiet is not None:
        level += parsed_args.quiet
    return level


def dedent_except_first_line(text: str) -> str:
    """Dedent all lines of text except the 1st, using textwrap.dedent()."""
    try:
        newline = text.index('\n') + 1
    except ValueError:
        return text
    return text[:newline] + textwrap.dedent(text[newline:])
