"""Unit tests for ingit command-line interface."""

import contextlib
import logging
import os
import platform
import shutil
import tempfile
import unittest

import psutil

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

    def test_help(self):
        with open(os.devnull, 'a') as devnull:
            for flags in (['-h'], ['--help']):
                with self.assertRaises(SystemExit):
                    with contextlib.redirect_stdout(devnull):
                        main(flags)

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
