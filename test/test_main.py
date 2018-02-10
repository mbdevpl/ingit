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

import ingit.runtime
from ingit.json_config import normalize_path
from ingit.runtime import RUNTIME_CONFIG_PATH, REPOS_CONFIG_PATH
from ingit.main import main

_LOG = logging.getLogger(__name__)


class Tests(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.repos_path = pathlib.Path(self._tmpdir.name)

    def tearDown(self):
        if platform.system() != 'Windows':
            self._tmpdir.cleanup()

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

    def test_clone(self):
        with unittest.mock.patch.object(ingit.runtime, 'find_repos_path',
                                        return_value=self.repos_path):
            main(['--config', 'test/examples/runtime_config/example1.json',
                  '--repos', 'test/examples/repos_config/example1.json', 'clone'])

    def test_init(self):
        with unittest.mock.patch.object(ingit.runtime, 'find_repos_path',
                                        return_value=self.repos_path):
            main(['--config', 'test/examples/runtime_config/example1.json',
                  '--repos', 'test/examples/repos_config/example1.json', 'init'])

    def test_gc(self):
        with unittest.mock.patch.object(ingit.runtime, 'find_repos_path',
                                        return_value=self.repos_path):
            main(['--config', 'test/examples/runtime_config/example1.json',
              '--repos', 'test/examples/repos_config/example1.json', 'clone'])
            main(['--config', 'test/examples/runtime_config/example1.json',
                  '--repos', 'test/examples/repos_config/example1.json', 'gc'])

    def test_status(self):
        with unittest.mock.patch.object(ingit.runtime, 'find_repos_path',
                                        return_value=self.repos_path):
            main(['--config', 'test/examples/runtime_config/example1.json',
              '--repos', 'test/examples/repos_config/example1.json', 'clone'])
            main(['--config', 'test/examples/runtime_config/example1.json',
                  '--repos', 'test/examples/repos_config/example1.json', 'status'])
