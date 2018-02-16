"""Unit tests for ingit command-line interface."""

import contextlib
import logging
import os
import pathlib
import platform
import tempfile
import unittest
import unittest.mock

import git
import readchar

from ingit.json_config import normalize_path, file_to_json
from ingit.runtime import \
    RUNTIME_CONFIG_PATH, REPOS_CONFIG_PATH, \
    acquire_runtime_configuration, acquire_repos_configuration
from ingit.main import main
from .test_setup import run_module

_LOG = logging.getLogger(__name__)

HERE = pathlib.Path(__file__).resolve().parent

TEST_RUNTIME_CONFIG_PATH = pathlib.Path(HERE, 'examples', 'runtime_config', 'example_initial.json')
TEST_RUNTIME_CONFIG = file_to_json(TEST_RUNTIME_CONFIG_PATH)

TEST_REPOS_CONFIG_PATH = pathlib.Path(HERE, 'examples', 'repos_config', 'example_initial.json')
TEST_REPOS_CONFIG = file_to_json(TEST_REPOS_CONFIG_PATH)

PROJECT_NAMES = ('argunparse', 'ingit', 'transpyle', 'typed-astunparse')


class Tests(unittest.TestCase):

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


class RuntimeCommandTests(unittest.TestCase):

    def setUp(self):
        with tempfile.NamedTemporaryFile() as tmp_file:
            self.runtime_config_path = pathlib.Path(tmp_file.name)
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            self.runtime_config = acquire_runtime_configuration(self.runtime_config_path)
        with tempfile.NamedTemporaryFile() as tmp_file:
            self.repos_config_path = pathlib.Path(tmp_file.name)
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            self.repos_config = acquire_repos_configuration(self.repos_config_path)

    def tearDown(self):
        self.repos_config_path.unlink()
        self.runtime_config_path.unlink()

    def call_main(self, *args, answer='y'):
        with unittest.mock.patch.object(readchar, 'readchar', return_value=answer):
            main(['--config', str(self.runtime_config_path), '--repos', str(self.repos_config_path)]
                 + list(args))

    def test_register(self):
        repo_paths = [
            pathlib.Path('..', 'argunparse'), pathlib.Path('..', 'ingit'),
            pathlib.Path('..', 'transpyle'), pathlib.Path('..', 'typed-astunparse')]
        for i, repo_path in enumerate(repo_paths):
            self.assertEqual(len(self.repos_config['repos']), i)
            self.call_main('register', str(repo_path))
            self.repos_config = acquire_repos_configuration(self.repos_config_path)
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

    def test_register_from_elsewhere(self):
        cwd = pathlib.Path(os.getcwd())
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            repo_path = pathlib.Path(cwd, '..', 'argunparse')
            self.call_main('register', str(repo_path))
            os.chdir(str(cwd))
        self.repos_config = acquire_repos_configuration(self.repos_config_path)
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


def call_main(*args, answer='y'):
    with unittest.mock.patch.object(readchar, 'readchar', return_value=answer):
        main(['--config', str(TEST_RUNTIME_CONFIG_PATH), '--repos', str(TEST_REPOS_CONFIG_PATH)]
             + list(args))


class GitCommandTests(unittest.TestCase):

    def setUp(self):
        assert 'INGIT_TEST_REPOS_PATH' not in os.environ
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ['INGIT_TEST_REPOS_PATH'] = self._tmpdir.name
        _LOG.warning('set INGIT_TEST_REPOS_PATH="%s"', self._tmpdir.name)
        self.repos_path = pathlib.Path(self._tmpdir.name)

    def tearDown(self):
        if platform.system() != 'Windows':
            self._tmpdir.cleanup()
        del os.environ['INGIT_TEST_REPOS_PATH']

    def test_clone(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            self.assertFalse(repo_path.is_dir())
            call_main('-p', 'name == "{}"'.format(project_name), 'clone')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())

    def test_clone_to_repo_dir(self):
        project_name = 'argunparse'
        repo_path = pathlib.Path(self.repos_path, project_name)
        call_main('-p', 'name == "{}"'.format(project_name), 'clone')
        self.assertTrue(repo_path.is_dir())
        self.assertTrue(repo_path.joinpath('.git').is_dir())
        call_main('-r', '^{}$'.format(project_name), 'clone')

    def test_clone_to_nonrepo_dir(self):
        project_name = 'argunparse'
        repo_path = pathlib.Path(self.repos_path, project_name)
        repo_path.mkdir()
        with self.assertRaises(ValueError):
            call_main('-p', 'name == "{}"'.format(project_name), 'clone')
        self.assertTrue(repo_path.is_dir())

    def test_init(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            self.assertFalse(repo_path.is_dir())
            call_main('-p', 'name == "{}"'.format(project_name), 'init')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())

    def test_init_in_repo_dir(self):
        project_name = 'argunparse'
        repo_path = pathlib.Path(self.repos_path, project_name)
        call_main('-p', 'name == "{}"'.format(project_name), 'clone')
        self.assertTrue(repo_path.is_dir())
        self.assertTrue(repo_path.joinpath('.git').is_dir())
        call_main('-p', 'name == "{}"'.format(project_name), 'init')

    def test_init_no(self):
        project_name = 'argunparse'
        call_main('-p', 'name == "{}"'.format(project_name), 'init')
        project_name = 'ingit'
        repo_path = pathlib.Path(self.repos_path, project_name)
        call_main('-p', 'name == "{}"'.format(project_name), 'init', answer='n')
        self.assertFalse(repo_path.is_dir())

    def test_fetch(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            call_main('-p', 'name == "{}"'.format(project_name), 'init')
            call_main('-p', 'name == "{}"'.format(project_name), 'fetch')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())

    def test_fetch_all(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            call_main('-p', 'name == "{}"'.format(project_name), 'init')
            call_main('-p', 'name == "{}"'.format(project_name), 'fetch', '--all')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())

    def test_checkout(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            call_main('-p', 'name == "{}"'.format(project_name), 'clone')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())
            call_main('-p', 'name == "{}"'.format(project_name), 'checkout', answer='n')

    def test_merge(self):
        pass

    def test_gc(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            call_main('-p', 'name == "{}"'.format(project_name), 'clone')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())
            call_main('-p', 'name == "{}"'.format(project_name), 'gc')

    def test_status(self):
        for project_name in PROJECT_NAMES:
            repo_path = pathlib.Path(self.repos_path, project_name)
            call_main('-p', 'name == "{}"'.format(project_name), 'clone')
            self.assertTrue(repo_path.is_dir())
            self.assertTrue(repo_path.joinpath('.git').is_dir())
            call_main('-p', 'name == "{}"'.format(project_name), 'status', answer='n')
