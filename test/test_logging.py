"""Unit tests for logging boilerplate."""

import inspect
import logging
import os
import pathlib
import unittest
import unittest.mock

from ingit.logging_boilerplate import \
    DEFAULT_LEVEL, logging_level_from_envvar, \
    log_filename_basic, log_filename_daily, log_filename_precise, \
    Logging, unittest_verbosity, StreamToCall

__version__ = '2022.08.15'


class LoggingTests(unittest.TestCase):

    def test_configure_basic(self):
        Logging.enable_console = True
        Logging.enable_file = False
        with unittest.mock.patch.object(logging, 'basicConfig') as mocked:
            Logging.configure_basic()
            self.assertEqual(mocked.call_args.args, ())
            self.assertIn('level', mocked.call_args.kwargs)
            self.assertIn('handlers', mocked.call_args.kwargs)
            self.assertNotIn('filename', mocked.call_args.kwargs)
        Logging.enable_console = False
        with unittest.mock.patch.object(logging, 'basicConfig') as mocked:
            Logging.configure_basic()
            self.assertNotIn('handlers', mocked.call_args.kwargs)
            self.assertNotIn('filename', mocked.call_args.kwargs)
        Logging.enable_file = True
        Logging.directory = 'my_software'
        with unittest.mock.patch.object(logging, 'basicConfig') as mocked:
            with unittest.mock.patch.object(pathlib.Path, 'mkdir', return_value=None):
                Logging.configure_basic()
            self.assertNotIn('handlers', mocked.call_args.kwargs)
            self.assertIn('filename', mocked.call_args.kwargs)

    def test_configure(self):
        Logging.directory = 'my_software'
        for enable_console, enable_file in (
                (False, False), (True, False), (False, True)):
            Logging.enable_console = enable_console
            Logging.enable_file = enable_file
            with unittest.mock.patch.object(logging.config, 'dictConfig') as mocked:
                with (
                        unittest.mock.patch.object(pathlib.Path, 'mkdir', return_value=None),
                        unittest.mock.patch.object(pathlib.Path, 'is_dir', return_value=True)):
                    Logging.configure()
                arg = mocked.call_args.args[0]
                if enable_console:
                    self.assertIn('console', arg['root']['handlers'])
                if enable_file:
                    self.assertIn('file', arg['root']['handlers'])

    def test_configure_from_json(self):
        with self.assertRaises(NotImplementedError):
            Logging.configure_from_json()


class UtilityTests(unittest.TestCase):

    def test_logging_level_from_envvar(self):
        envvar = 'MY_UNIQUE_ENVVAR_FOR_TESTING'
        self.assertEqual(logging_level_from_envvar(envvar), DEFAULT_LEVEL)
        os.environ[envvar] = 'debug'
        self.assertEqual(logging_level_from_envvar(envvar), logging.DEBUG)
        os.environ[envvar] = 'debugging'
        self.assertEqual(logging_level_from_envvar(envvar), DEFAULT_LEVEL)
        os.environ[envvar] = '35'
        self.assertEqual(logging_level_from_envvar(envvar), 35)
        del os.environ[envvar]

    def test_log_filename_basic(self):
        self.assertEqual(log_filename_basic('my_software'), 'my_software.log')

    def test_log_filename_daily(self):
        filename = log_filename_daily('my_software')
        self.assertTrue(filename.startswith('my_software_'))
        self.assertTrue(filename.endswith('.log'))

    def test_log_filename_precise(self):
        filename = log_filename_precise('my_software')
        self.assertTrue(filename.startswith('my_software_'))
        self.assertTrue(filename.endswith('.log'))

    def test_unittest_verbosity(self):
        verbosity = unittest_verbosity()
        self.assertIsInstance(verbosity, int)

    def test_unittest_verbosity_not_unittest(self):
        with unittest.mock.patch.object(inspect, 'currentframe', return_value=False):
            verbosity = unittest_verbosity()
        self.assertIsNone(verbosity)

    def test_stream_to_call(self):
        log = logging.getLogger(f'{__name__}.test_stream_to_call')
        stream = StreamToCall(log.info)
        print('test output', file=stream)
