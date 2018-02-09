"""Unit tests for ingit runtime."""

import logging
import os
import pathlib
import tempfile
import unittest
import unittest.mock

import readchar

from ingit.runtime import \
    RUNTIME_CONFIG_PATH, REPOS_CONFIG_PATH, \
    default_runtime_configuration, acquire_runtime_configuration, \
    default_repos_configuration, acquire_repos_configuration

_LOG = logging.getLogger(__name__)


class Tests(unittest.TestCase):

    def test_create_runtime_config(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
            with tempfile.NamedTemporaryFile() as tmp_file:
                path = pathlib.Path(tmp_file.name)
            with self.assertRaises(FileNotFoundError):
                acquire_runtime_configuration(path)

        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            with tempfile.NamedTemporaryFile() as tmp_file:
                path = pathlib.Path(tmp_file.name)
            runtime_config = acquire_runtime_configuration(path)
            path.unlink()
            self.assertEqual(runtime_config, default_runtime_configuration())

    @unittest.skipUnless('CI' in os.environ, 'skipping test that affects user environment')
    def test_use_default_config_dir(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            runtime_config = acquire_runtime_configuration(RUNTIME_CONFIG_PATH)
            RUNTIME_CONFIG_PATH.unlink()
            self.assertEqual(runtime_config, default_runtime_configuration())
            repos_config = acquire_repos_configuration(REPOS_CONFIG_PATH)
            REPOS_CONFIG_PATH.unlink()
            self.assertEqual(repos_config, default_repos_configuration())


    def test_create_repos_config(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
            with tempfile.NamedTemporaryFile() as tmp_file:
                path = pathlib.Path(tmp_file.name)
            with self.assertRaises(FileNotFoundError):
                acquire_repos_configuration(path)

        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            with tempfile.NamedTemporaryFile() as tmp_file:
                path = pathlib.Path(tmp_file.name)
            repos_config = acquire_repos_configuration(path)
            path.unlink()
            self.assertEqual(repos_config, default_repos_configuration())

    def test_acquire_runtime_config(self):
        paths = [
            pathlib.Path('~/.ingit_config.json'),
            pathlib.Path('~/.ingit_config.json'),
            pathlib.Path('test/examples/runtime_config/example1.json')
            ]
