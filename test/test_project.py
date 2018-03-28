"""Unit tests for operations on a single project."""

import logging
import pathlib
import unittest
import unittest.mock

# import git
import readchar

from ingit.project import Project
from .git_repo_tests import GitRepoTests

_HERE = pathlib.Path(__file__).resolve().parent

_REMOTE = str(_HERE.parent.joinpath('.git'))

_LOG = logging.getLogger(__name__)


class Tests(GitRepoTests):

    def test_example(self):
        project = Project('example', ['tag1', 'tag2'], self.repo_path, {})
        self.assertEqual(project.name, 'example')
        self.assertSetEqual(project.tags, {'tag1', 'tag2'})

    def test_clone(self):
        project = Project('example', [], self.repo_path.joinpath('example'), {'origin': _REMOTE})
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            project.clone()
        self.assertTrue(self.repo_path.joinpath('example', '.git').is_dir())

    def test_clone_existing_dir(self):
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            with self.assertRaises(ValueError):
                project.clone()

    def test_clone_initialized(self):
        self.git_init()
        project = Project('example', [], self.repo_path, {})
        project.clone()

    def test_clone_no_remote(self):
        project = Project('example', [], self.repo_path.joinpath('example'), {})
        with self.assertRaises(StopIteration):
            project.clone()

    def test_clone_no(self):
        project = Project('example', [], self.repo_path.joinpath('example'), {'origin': _REMOTE})
        with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
            project.clone()
        self.assertFalse(self.repo_path.joinpath('example', '.git').is_dir())

    def test_init(self):
        project = Project('example', [], self.repo_path.joinpath('example'), {})
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            project.init()
        self.assertTrue(self.repo_path.joinpath('example', '.git').is_dir())

    def test_init_existing(self):
        project = Project('example', [], self.repo_path, {})
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            with self.assertRaises(ValueError):
                project.init()

    def test_init_initialized(self):
        self.git_init()
        project = Project('example', [], self.repo_path, {})
        project.init()

    def test_init_no(self):
        project = Project('example', [], self.repo_path.joinpath('example'), {})
        with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
            project.init()
        self.assertFalse(self.repo_path.joinpath('example', '.git').is_dir())

    # def test_fetch(self):
    #    pass

    # def test_fetch_all(self):
    #    pass

    # def test_checkout(self):
    #    pass

    # @unittest.expectedFailure
    # def test_merge(self):
    #    pass

    # @unittest.expectedFailure
    # def test_push(self):
    #    pass

    # def test_gc(self):
    #    pass

    def test_status(self):
        self.git_init()
        self.repo.git.remote('add', 'origin', _REMOTE)
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        project.status()

    def test_status_unclear(self):
        self.git_init()
        self.repo.git.remote('add', 'origin', _REMOTE)
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        path = self.git_commit_new_file()
        self.git_modify_file(path)
        project.status()
        self.git_modify_file(path, add=True)
        project.status()
        self.git_modify_file(path, commit=True)
        project.status()

    def test_status_not_pushed(self):
        self.git_clone('origin', _REMOTE)
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        self.git_commit_new_file()
        project.status()

    def test_status_not_pushed_many(self):
        self.git_clone('origin', _REMOTE)
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        for _ in range(10 + 10 + 1 + 1):
            self.git_commit_new_file()
        project.status()

    def test_status_not_merged(self):
        self.git_clone('origin', _REMOTE)
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        self.repo.git.reset('--hard', 'HEAD~1')
        project.status()

    def test_status_extra_remote(self):
        self.git_init()
        self.repo.git.remote('add', 'origin', _REMOTE)
        self.repo.git.remote('add', 'mirror', _REMOTE)
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        project.status()

    def test_status_missing_remote(self):
        self.git_init()
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            project.status()
        self.assertIn('origin', self.repo.git.remote(v=True))
        self.assertIn(_REMOTE, self.repo.git.remote(v=True))

    def test_status_missing_remote_no(self):
        self.git_init()
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
            project.status()
        self.assertNotIn('origin', self.repo.git.remote(v=True))
        self.assertNotIn(_REMOTE, self.repo.git.remote(v=True))

    def test_status_bad_remote(self):
        self.git_init()
        self.repo.git.remote('add', 'mirror', _REMOTE)
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        project.status()
        self.assertNotIn('origin', self.repo.git.remote(v=True))
        self.assertIn(_REMOTE, self.repo.git.remote(v=True))
