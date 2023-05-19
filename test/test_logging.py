"""Unit tests for logging boilerplate."""

import inspect
import logging
import os
import pathlib
import tempfile
import unittest
import unittest.mock

from ingit import logging_boilerplate

__version__ = '2023.05.19'


class ExampleLogging(logging_boilerplate.Logging):
    packages = ['my_software']
    enable_console = True
    enable_file = False
    directory = 'my_software'


class LoggingTests(unittest.TestCase):

    def setUp(self):
        patcher1 = unittest.mock.patch.object(
            logging_boilerplate, 'LOGS_PATH', pathlib.Path(tempfile.gettempdir()))
        patcher1.start()
        self.addCleanup(patcher1.stop)
        patcher2 = unittest.mock.patch.object(logging, 'getLogger')
        patcher2.start()
        self.addCleanup(patcher2.stop)

    def test_configure_basic(self):
        ExampleLogging.packages = ['my_software']
        ExampleLogging.enable_console = True
        ExampleLogging.enable_file = False
        with unittest.mock.patch.object(logging, 'basicConfig') as mocked:
            ExampleLogging.configure_basic()
            self.assertEqual(mocked.call_args.args, (), msg=mocked.call_args)
            self.assertIn('level', mocked.call_args.kwargs, msg=mocked.call_args)
            self.assertIn('handlers', mocked.call_args.kwargs, msg=mocked.call_args)
            self.assertNotIn('filename', mocked.call_args.kwargs, msg=mocked.call_args)
        ExampleLogging.enable_console = False
        with unittest.mock.patch.object(logging, 'basicConfig') as mocked:
            ExampleLogging.configure_basic()
            self.assertNotIn('handlers', mocked.call_args.kwargs, msg=mocked.call_args)
            self.assertNotIn('filename', mocked.call_args.kwargs, msg=mocked.call_args)
        ExampleLogging.enable_file = True
        ExampleLogging.directory = 'my_software'
        with unittest.mock.patch.object(logging, 'basicConfig') as mocked:
            with unittest.mock.patch.object(pathlib.Path, 'mkdir', return_value=None):
                ExampleLogging.configure_basic()
            self.assertNotIn('handlers', mocked.call_args.kwargs, msg=mocked.call_args)
            self.assertIn('filename', mocked.call_args.kwargs, msg=mocked.call_args)

    def test_configure(self):
        ExampleLogging.directory = 'my_software'
        for enable_console, enable_file in (
                (False, False), (True, False), (False, True)):
            ExampleLogging.enable_console = enable_console
            ExampleLogging.enable_file = enable_file
            with unittest.mock.patch.object(logging.config, 'dictConfig') as mocked:
                with unittest.mock.patch.object(pathlib.Path, 'is_dir', return_value=True):
                    ExampleLogging.configure()
                arg = mocked.call_args.args[0]
                if enable_console:
                    self.assertIn('console', arg['root']['handlers'], msg=mocked.call_args)
                if enable_file:
                    self.assertIn('file', arg['root']['handlers'], msg=mocked.call_args)


class UtilityTests(unittest.TestCase):

    def test_logging_level_from_envvar(self):
        envvar = 'MY_UNIQUE_ENVVAR_FOR_TESTING'
        self.assertEqual(logging_boilerplate.logging_level_from_envvar(envvar, default=42), 42)
        os.environ[envvar] = 'debug'
        self.assertEqual(logging_boilerplate.logging_level_from_envvar(envvar), logging.DEBUG)
        os.environ[envvar] = 'debugging'
        self.assertEqual(logging_boilerplate.logging_level_from_envvar(envvar, default=42), 42)
        os.environ[envvar] = '35'
        self.assertEqual(logging_boilerplate.logging_level_from_envvar(envvar), 35)
        del os.environ[envvar]

    def test_log_filename_basic(self):
        self.assertEqual(logging_boilerplate.log_filename_basic('my_software'), 'my_software.log')

    def test_log_filename_daily(self):
        filename = logging_boilerplate.log_filename_daily('my_software')
        self.assertTrue(filename.startswith('my_software_'))
        self.assertTrue(filename.endswith('.log'))

    def test_log_filename_precise(self):
        filename = logging_boilerplate.log_filename_precise('my_software')
        self.assertTrue(filename.startswith('my_software_'))
        self.assertTrue(filename.endswith('.log'))

    def test_unittest_verbosity(self):
        verbosity = logging_boilerplate.unittest_verbosity()
        self.assertIsInstance(verbosity, int)

    def test_unittest_verbosity_not_unittest(self):
        with unittest.mock.patch.object(inspect, 'currentframe', return_value=False):
            verbosity = logging_boilerplate.unittest_verbosity()
        self.assertIsNone(verbosity)

    def test_stream_to_call(self):
        log = logging.getLogger(f'{__name__}.test_stream_to_call')
        stream = logging_boilerplate.StreamToCall(log.info)
        print('test output', file=stream)
