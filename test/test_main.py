"""Unit tests for ingit command-line interface."""

import contextlib
import os
import shutil
import unittest

from ingit.main import main


class Tests(unittest.TestCase):

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

    def tearDown(self):
        if os.path.isdir('/tmp/ingit'):
            shutil.rmtree('/tmp/ingit')
