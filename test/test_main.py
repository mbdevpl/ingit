"""Unit tests for ingit command-line interface."""

import contextlib
import logging
import os
import platform
import shutil
import tempfile
import unittest

import psutil
import readchar

from ingit.runtime import RUNTIME_CONFIG_PATH, REPOS_CONFIG_PATH
from ingit.main import main

_LOG = logging.getLogger(__name__)


class Tests(unittest.TestCase):

    def tearDown(self):
        if platform.system() == 'Windows':
            git_processes = [_ for _ in psutil.process_iter() if 'git' in _.name()]
            for git_process in git_processes:
                _LOG.warning('killing %s ...', git_process)
                git_process.kill(git_process)

        path = os.path.join(tempfile.gettempdir(), 'ingit')
        if os.path.isdir(path):
            shutil.rmtree(path)

    @classmethod
    def tearDownClass(cls):
        if platform.system() == 'Windows':
            all_processes = [_ for _ in psutil.process_iter()]
            for process in all_processes:
                _LOG.warning('process: %s', process)

    def test_help(self):
        with open(os.devnull, 'a') as devnull:
            for flags in (['-h'], ['--help']):
                with self.assertRaises(SystemExit):
                    with contextlib.redirect_stdout(devnull):
                        main(flags)

    @unittest.skipUnless('CI' in os.environ, 'skipping test that affects user environment')
    def test_create_configs(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            self.assertFalse(RUNTIME_CONFIG_PATH.exists())
            self.assertFalse(REPOS_CONFIG_PATH.exists())
            main(['register'])
            self.assertTrue(RUNTIME_CONFIG_PATH.exists())
            self.assertTrue(REPOS_CONFIG_PATH.exists())
            RUNTIME_CONFIG_PATH.unlink()
            REPOS_CONFIG_PATH.unlink()

    def test_clone(self):
        main(['--config', 'test/examples/runtime_config/example1.json',
              '--repos', 'test/examples/repos_config/example1.json', 'clone'])

    def test_init(self):
        main(['--config', 'test/examples/runtime_config/example1.json',
              '--repos', 'test/examples/repos_config/example1.json', 'init'])

    def test_gc(self):
        main(['--config', 'test/examples/runtime_config/example1.json',
              '--repos', 'test/examples/repos_config/example1.json', 'clone'])
        main(['--config', 'test/examples/runtime_config/example1.json',
              '--repos', 'test/examples/repos_config/example1.json', 'gc'])

    def test_status(self):
        main(['--config', 'test/examples/runtime_config/example1.json',
              '--repos', 'test/examples/repos_config/example1.json', 'clone'])
        main(['--config', 'test/examples/runtime_config/example1.json',
              '--repos', 'test/examples/repos_config/example1.json', 'status'])
