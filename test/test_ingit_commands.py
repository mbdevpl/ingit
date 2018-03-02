"""Unit tests for ingit-only commands of ingit."""

import os
import pathlib
import tempfile
import unittest
import unittest.mock

import git
import readchar

from ingit.json_config import normalize_path, json_to_file, acquire_configuration
from ingit.main import main


class Tests(unittest.TestCase):

    def setUp(self):
        with tempfile.NamedTemporaryFile() as tmp_file:
            self.runtime_config_path = pathlib.Path(tmp_file.name)
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            self.runtime_config = acquire_configuration(self.runtime_config_path, 'runtime')
        with tempfile.NamedTemporaryFile() as tmp_file:
            self.repos_config_path = pathlib.Path(tmp_file.name)
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            self.repos_config = acquire_configuration(self.repos_config_path, 'repos')

    def tearDown(self):
        self.repos_config_path.unlink()
        self.runtime_config_path.unlink()

    def call_main(self, *args, answer='y'):
        with unittest.mock.patch.object(readchar, 'readchar', return_value=answer):
            main(['--config', str(self.runtime_config_path), '--repos', str(self.repos_config_path)]
                 + list(args))

    def test_summary(self):
        repo_paths = [
            pathlib.Path('..', 'argunparse'), pathlib.Path('..', 'ingit'),
            pathlib.Path('..', 'transpyle'), pathlib.Path('..', 'typed-astunparse')]
        for i, repo_path in enumerate(repo_paths):
            # self.assertEqual(len(self.repos_config['repos']), i)
            self.call_main('register', str(repo_path))
            # self.repos_config = acquire_configuration(self.repos_config_path, 'repos')
            # self.assertEqual(len(self.repos_config['repos']), i + 1)
            self.call_main('summary')

    def test_summary_empty(self):
        self.call_main('summary')

    def test_register(self):
        repo_paths = [
            pathlib.Path('..', 'argunparse'), pathlib.Path('..', 'ingit'),
            pathlib.Path('..', 'transpyle'), pathlib.Path('..', 'typed-astunparse')]
        for i, repo_path in enumerate(repo_paths):
            self.assertEqual(len(self.repos_config['repos']), i)
            self.call_main('register', str(repo_path))
            self.repos_config = acquire_configuration(self.repos_config_path, 'repos')
            self.assertEqual(len(self.repos_config['repos']), i + 1)

    def test_register_with_tags(self):
        repo_paths = [
            pathlib.Path('..', 'argunparse'), pathlib.Path('..', 'ingit'),
            pathlib.Path('..', 'transpyle'), pathlib.Path('..', 'typed-astunparse')]
        for i, repo_path in enumerate(repo_paths):
            self.assertEqual(len(self.repos_config['repos']), i)
            self.call_main('register', str(repo_path),
                           '--tags', *['tag{}'.format(_) for _ in range(1, i + 2)])
            self.repos_config = acquire_configuration(self.repos_config_path, 'repos')
            self.assertEqual(len(self.repos_config['repos']), i + 1)

    def test_register_equivalents(self):
        path1 = pathlib.Path('.')
        path2 = pathlib.Path('.').resolve()
        path3 = pathlib.Path('..', 'ingit')
        self.call_main('register')
        with self.assertRaises(ValueError):
            self.call_main('register', str(path1))
        with self.assertRaises(ValueError):
            self.call_main('register', str(path2))
        with self.assertRaises(ValueError):
            self.call_main('register', str(path3))

    def test_register_outside(self):
        self.runtime_config['machines'][0]['repos_root'] = str(tempfile.gettempprefix())
        json_to_file(self.runtime_config, self.runtime_config_path)
        # self.runtime_config = acquire_configuration(self.runtime_config_path, 'runtime')
        repo_path = pathlib.Path('..', 'ingit')
        self.call_main('register', str(repo_path))

    def test_register_from_elsewhere(self):
        cwd = pathlib.Path(os.getcwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            repo_path = pathlib.Path(cwd, '..', 'argunparse')
            self.call_main('register', str(repo_path))
            os.chdir(str(cwd))
        self.repos_config = acquire_configuration(self.repos_config_path, 'repos')
        self.assertEqual(len(self.repos_config['repos']), 1)
        repo_config = self.repos_config['repos'][0]
        repos_path = normalize_path(self.runtime_config['machines'][0]['repos_path'])
        self.assertEqual(repo_path.resolve(), pathlib.Path(repos_path, repo_config['path']))

    def test_register_nonrepo(self):
        repo_path = pathlib.Path('blah blah blah')
        with self.assertRaises(git.exc.NoSuchPathError):
            self.call_main('register', str(repo_path))
        repo_path = pathlib.Path('test', 'examples')
        with self.assertRaises(git.exc.InvalidGitRepositoryError):
            self.call_main('register', str(repo_path))
