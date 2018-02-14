"""Unit tests for ingit command-line interface."""

import contextlib
import logging
import os
import pathlib
import platform
import tempfile
import unittest
import unittest.mock

import readchar

from ingit.json_config import normalize_path
from ingit.runtime import RUNTIME_CONFIG_PATH, REPOS_CONFIG_PATH
from ingit.main import main
from .test_setup import run_module

_LOG = logging.getLogger(__name__)


class Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        assert 'INGIT_TEST_REPOS_PATH' not in os.environ
        cls._tmpdir = tempfile.TemporaryDirectory()
        os.environ['INGIT_TEST_REPOS_PATH'] = cls._tmpdir.name
        _LOG.warning('set INGIT_TEST_REPOS_PATH="%s"', cls._tmpdir.name)
        cls.repos_path = pathlib.Path(cls._tmpdir.name)
        # raise NotImplementedError()
        # _ = os.environ['INGIT_TEST_REPOS_PATH']

    @classmethod
    def tearDownClass(cls):
        if platform.system() != 'Windows':
            cls._tmpdir.cleanup()

    def test_script(self):
        with self.assertRaises(SystemExit):
            run_module('ingit')
        run_module('ingit', run_name='not_main')

    def test_help(self):
        with open(os.devnull, 'a') as devnull:
            for flags in (['-h'], ['--help']):
                with self.assertRaises(SystemExit):
                    with contextlib.redirect_stdout(devnull):
                        main(flags)

    @unittest.skipUnless('CI' in os.environ, 'skipping test that affects user environment')
    def test_create_configs(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            runtime_config_path = normalize_path(RUNTIME_CONFIG_PATH)
            repos_config_path = normalize_path(REPOS_CONFIG_PATH)
            self.assertFalse(runtime_config_path.exists())
            self.assertFalse(repos_config_path.exists())
            main(['register'])
            self.assertTrue(runtime_config_path.exists())
            self.assertTrue(repos_config_path.exists())
            runtime_config_path.unlink()
            repos_config_path.unlink()

    def test_1(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            main(['--config', 'test/examples/runtime_config/example1.json',
                  '--repos', 'test/examples/repos_config/example1.json', 'clone'])
        self.assertTrue(pathlib.Path(self.repos_path, 'repos1').is_dir())

    def test_2_clone(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            main(['--config', 'test/examples/runtime_config/example2.json',
                  '--repos', 'test/examples/repos_config/example2.json',
                  '-p', 'name == "ingit"', 'clone'])
        self.assertTrue(pathlib.Path(self.repos_path, 'repos2', 'ingit').is_dir())

    def test_2_init_and_fetch(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            main(['--config', 'test/examples/runtime_config/example2.json',
                  '--repos', 'test/examples/repos_config/example2.json',
                  '-r', 'typed-astunparse', 'init'])
        self.assertTrue(pathlib.Path(self.repos_path, 'repos2', 'typed-astunparse').is_dir())
        self.assertTrue(
            pathlib.Path(self.repos_path, 'repos2', 'typed-astunparse', '.git').is_dir())
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            main(['--config', 'test/examples/runtime_config/example2.json',
                  '--repos', 'test/examples/repos_config/example2.json',
                  '-r', 'typed-astunparse', 'fetch', '--all'])
        self.assertTrue(pathlib.Path(self.repos_path, 'repos2', 'typed-astunparse').is_dir())

    def test_checkout(self):
        self.assertTrue(pathlib.Path(self.repos_path, 'repos2', 'ingit').is_dir())
        with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
            main(['--config', 'test/examples/runtime_config/example2.json',
                  '--repos', 'test/examples/repos_config/example2.json',
                  '-p', 'name == "ingit"', 'checkout'])

    def test_gc(self):
        self.assertTrue(pathlib.Path(self.repos_path, 'repos2', 'ingit').is_dir())
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            # main(['--config', 'test/examples/runtime_config/example1.json',
            #      '--repos', 'test/examples/repos_config/example1.json', 'clone'])
            main(['--config', 'test/examples/runtime_config/example1.json',
                  '--repos', 'test/examples/repos_config/example1.json',
                  '-r', 'ingit', 'gc'])

    def test_status(self):
        self.assertTrue(pathlib.Path(self.repos_path, 'repos2', 'typed-astunparse').is_dir())
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            # main(['--config', 'test/examples/runtime_config/example1.json',
            #      '--repos', 'test/examples/repos_config/example1.json', 'clone'])
            main(['--config', 'test/examples/runtime_config/example1.json',
                  '--repos', 'test/examples/repos_config/example1.json',
                  '-p', 'name == "types-astunparse"', 'status'])
