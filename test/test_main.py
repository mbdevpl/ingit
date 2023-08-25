"""Unit tests for ingit command-line interface."""

import contextlib
import os
import unittest
import unittest.mock

from boilerplates.packaging_tests import run_module
import readchar

from ingit.json_config import RUNTIME_CONFIG_PATH, REPOS_CONFIG_PATH, normalize_path
from ingit.main import main


class Tests(unittest.TestCase):

    def test_script(self):
        with self.assertRaises(SystemExit):
            run_module('ingit')
        run_module('ingit', run_name='not_main')

    def test_help(self):
        with open(os.devnull, 'a', encoding='utf-8') as devnull:
            for flags in (['-h'], ['--help']):
                with self.assertRaises(SystemExit):
                    with contextlib.redirect_stdout(devnull):
                        main(flags)

    def test_filtered_register(self):
        with self.assertRaises(SystemExit):
            main(['-p', 'something', 'register'])
        with self.assertRaises(SystemExit):
            main(['-r', 'True', 'register'])

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
