"""Unit tests for ingit runtime."""

import logging
import os
import pathlib
import shutil
import tempfile
import unittest
import unittest.mock

from boilerplates.config import normalize_path
import readchar

from ingit.json_config import \
    RUNTIME_CONFIG_PATH, REPOS_CONFIG_PATH, REPO_LISTS_DIRECTORY_NAME, \
    default_runtime_configuration, default_repos_configuration, acquire_configuration, \
    acquire_repos_configuration

_HERE = pathlib.Path(__file__).resolve().parent
_EXAMPLES_FOLDER = _HERE.joinpath('examples')
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
        bad_config_path = _EXAMPLES_FOLDER.joinpath('runtime_config', 'example_bad.json')
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

    def test_create_repos_config_with_extra(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with tempfile.NamedTemporaryFile(dir=tmp_dir) as tmp_file:
                path = pathlib.Path(tmp_file.name)
            _LOG.debug('temporary config path: %s', path)
            with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
                repos_config = acquire_repos_configuration(path)
            self.assertEqual(repos_config, default_repos_configuration())
            repo_lists_path = path.parent.joinpath(REPO_LISTS_DIRECTORY_NAME)
            _LOG.debug('repos lists path: %s', repo_lists_path)
            self.assertFalse(repo_lists_path.exists())
            repo_lists_path.mkdir()
            self.assertTrue(repo_lists_path.is_dir())
            repos_config = acquire_repos_configuration(path)
            self.assertEqual(repos_config, default_repos_configuration())
            extra_repos_config_path_source = _EXAMPLES_FOLDER.joinpath(
                'repos_config', 'repos.d', 'example_extra.json')
            extra_repos_config_path = repo_lists_path.joinpath('example_extra.json')
            shutil.copy(extra_repos_config_path_source, extra_repos_config_path)
            ignored_file_path = repo_lists_path.joinpath('ignored_file.txt')
            ignored_file_path.touch()
            repos_config = acquire_repos_configuration(path)
            self.assertNotEqual(repos_config, default_repos_configuration())
            self.assertIn('repos', repos_config)
            self.assertEqual(len(repos_config['repos']), 1)
            self.assertEqual(repos_config['repos'][0]['name'], 'nonexistent')
