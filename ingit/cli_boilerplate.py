"""Boilerplate useful when creating a command-line interface."""

import argparse
import logging
import sys
import textwrap
import typing as t

import argcomplete

from ._version import VERSION

__updated__ = '2020-01-29'

VERBOSITY_DEFAULT = (logging.CRITICAL - logging.WARNING) // 10  # integer from 0 to 5


class ArgumentDefaultsAndRawDescriptionHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Inherit from ArgumentDefaultsHelpFormatter and RawDescriptionHelpFormatter."""


def make_copyright_notice(
        year_from: int, year_to: t.Optional[int] = None, author: str = 'Mateusz Bysiek',
        license_name: str = 'Apache License 2.0', url: t.Optional[str] = None):
    """Assemble a copyright notice like "Copyright YYYY by Author(s). License Name. http://url/"."""
    if year_to is None or year_to == year_from:
        years = year_from
    else:
        years = '{}-{}'.format(year_from, year_to)
    return 'Copyright {} by {}. {}. {}'.format(
        years, author, license_name, '' if url is None else url).rstrip()


def add_version_option(parser: argparse.ArgumentParser):
    """Add --version option to a given parser."""
    parser.add_argument('--version', action='version',
                        version='ingit {}, Python {}'.format(VERSION, sys.version))


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
        help='set verbosity level explicitly (normally from {} to {})'.format(0, 5)) \
        .completer = argcomplete.completers.ChoicesCompleter(choices=list(range(0, 5 + 1, 1)))
    return verbosity_group


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
