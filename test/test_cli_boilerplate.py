"""Tests for the CLI boilerplate."""

import argparse
import contextlib
import logging
import pathlib
import unittest

from ingit import cli_boilerplate

__version__ = '2023.03.10'


class UnitTests(unittest.TestCase):
    """Test basic functionalities of the CLI boilerplate."""

    def test_copyright_notice(self):
        notice = cli_boilerplate.make_copyright_notice(2020)
        self.assertTrue(notice.startswith('Copyright 2020 '), msg=notice)
        notice = cli_boilerplate.make_copyright_notice(2020, 2020)
        self.assertTrue(notice.startswith('Copyright 2020 '), msg=notice)
        notice = cli_boilerplate.make_copyright_notice(2020, 2023)
        self.assertTrue(notice.startswith('Copyright 2020-2023 '), msg=notice)

    def test_version_option(self):
        parser = argparse.ArgumentParser('cli_boilerplate_test')
        cli_boilerplate.add_version_option(parser)
        with pathlib.Path('/dev/null').open('w', encoding='utf-8') as devnull:
            with contextlib.redirect_stderr(devnull):
                with self.assertRaises(SystemExit):
                    parser.parse_args(['--version'])

    def test_logging_level_conversion(self):
        for logging_level in (
                logging.NOTSET, logging.DEBUG, logging.WARNING, logging.ERROR, logging.CRITICAL):
            with self.subTest(logging_level=logging_level):
                verbosity = cli_boilerplate.logging_level_to_verbosity_level(logging_level)
                self.assertGreaterEqual(
                    verbosity, cli_boilerplate._VERBOSITY_MIN)  # pylint: disable=protected-access
                self.assertLessEqual(
                    verbosity, cli_boilerplate._VERBOSITY_MAX)  # pylint: disable=protected-access
                converted_logging_level = \
                    cli_boilerplate.verbosity_level_to_logging_level(verbosity)
                self.assertEqual(converted_logging_level, logging_level)

    def test_verbosity_level_conversion(self):
        for verbosity in range(-10, 10):
            with self.subTest(verbosity=verbosity):
                logging_level = cli_boilerplate.verbosity_level_to_logging_level(verbosity)
                converted_verbosity = \
                    cli_boilerplate.logging_level_to_verbosity_level(logging_level)
                self.assertEqual(converted_verbosity, verbosity)

    def test_verbosity_default(self):
        parser = argparse.ArgumentParser()
        cli_boilerplate.add_verbosity_group(parser)
        parsed_args = parser.parse_args([])
        verbosity = cli_boilerplate.get_verbosity_level(parsed_args)
        self.assertEqual(
            verbosity, cli_boilerplate._VERBOSITY_DEFAULT)  # pylint: disable=protected-access

    def test_verbosity_by_level(self):
        parser = argparse.ArgumentParser()
        cli_boilerplate.add_verbosity_group(parser)
        for verbosity in range(
                cli_boilerplate._VERBOSITY_MIN,  # pylint: disable=protected-access
                cli_boilerplate._VERBOSITY_MAX):  # pylint: disable=protected-access
            parsed_args = parser.parse_args([f'--verbosity={verbosity}'])
            parsed_verbosity = cli_boilerplate.get_verbosity_level(parsed_args)
            self.assertEqual(parsed_verbosity, verbosity)
            logging_level = cli_boilerplate.get_logging_level(parsed_args)
            self.assertEqual(
                logging_level, cli_boilerplate.verbosity_level_to_logging_level(verbosity))

    def test_verbosity_by_flags(self):
        parser = argparse.ArgumentParser()
        cli_boilerplate.add_verbosity_group(parser)
        for flags, verbosity_change, in {
                ('-v',): 1,
                ('--verbose',): 1,
                ('-v', '-v'): 2,
                ('-vv',): 2,
                ('-q',): -1,
                ('--quiet',): -1,
                ('-q', '-q'): -2,
                ('-qq',): -2
                }.items():
            parsed_args = parser.parse_args(flags)
            verbosity = cli_boilerplate.get_verbosity_level(parsed_args)
            # pylint: disable=protected-access
            self.assertEqual(verbosity, cli_boilerplate._VERBOSITY_DEFAULT + verbosity_change)

    def test_too_many_verbosity_flags(self):
        parser = argparse.ArgumentParser()
        cli_boilerplate.add_verbosity_group(parser)
        # pylint: disable=protected-access
        for flags in (
                [f'-{"v" * (cli_boilerplate._VERBOSE_MAX_COUNT + 1)}'],
                [f'-{"v" * (cli_boilerplate._VERBOSE_MAX_COUNT + 2)}'],
                [f'-{"q" * (cli_boilerplate._QUIET_MAX_COUNT + 1)}'],
                [f'-{"q" * (cli_boilerplate._QUIET_MAX_COUNT + 2)}']):
            parsed_args = parser.parse_args(flags)
            with self.assertRaises(ValueError):
                cli_boilerplate.get_verbosity_level(parsed_args)

    def test_dedent_except_first_line(self):
        self.assertEqual(
            cli_boilerplate.dedent_except_first_line('  test'), '  test')
        self.assertEqual(
            cli_boilerplate.dedent_except_first_line('  test\n  test'), '  test\ntest')
