"""Unit tests for ingit runtime."""

import logging
import os
import pathlib
import tempfile
import unittest
import unittest.mock

from boilerplates.config import normalize_path
import readchar

from ingit.json_config import \
    RUNTIME_CONFIG_PATH, REPOS_CONFIG_PATH, \
    default_runtime_configuration, default_repos_configuration, acquire_configuration

_LOG = logging.getLogger(__name__)


class Tests(unittest.TestCase):

    def test_create_runtime_config(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
            with tempfile.NamedTemporaryFile() as tmp_file:
                path = pathlib.Path(tmp_file.name)
            with self.assertRaises(FileNotFoundError):
                acquire_configuration(path, 'runtime')

        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            with tempfile.NamedTemporaryFile() as tmp_file:
                path = pathlib.Path(tmp_file.name)
            runtime_config = acquire_configuration(path, 'runtime')
            path.unlink()
            self.assertEqual(runtime_config, default_runtime_configuration())

    def test_bad_runtime_config(self):
        bad_config_path = pathlib.Path('test', 'examples', 'runtime_config', 'example_bad.json')
        with self.assertRaises(ValueError):
            acquire_configuration(bad_config_path, 'runtime')

    @unittest.skipUnless('CI' in os.environ, 'skipping test that affects user environment')
    def test_use_default_config_dir(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            runtime_config = acquire_configuration(RUNTIME_CONFIG_PATH, 'runtime')
            runtime_config_path = normalize_path(RUNTIME_CONFIG_PATH)
            runtime_config_path.unlink()
            self.assertEqual(runtime_config, default_runtime_configuration())
            repos_config = acquire_configuration(REPOS_CONFIG_PATH, 'repos')
            repos_config_path = normalize_path(REPOS_CONFIG_PATH)
            repos_config_path.unlink()
            self.assertEqual(repos_config, default_repos_configuration())

    def test_create_repos_config(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
            with tempfile.NamedTemporaryFile() as tmp_file:
                path = pathlib.Path(tmp_file.name)
            with self.assertRaises(FileNotFoundError):
                acquire_configuration(path, 'repos')

        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            with tempfile.NamedTemporaryFile() as tmp_file:
                path = pathlib.Path(tmp_file.name)
            repos_config = acquire_configuration(path, 'repos')
            path.unlink()
            self.assertEqual(repos_config, default_repos_configuration())
