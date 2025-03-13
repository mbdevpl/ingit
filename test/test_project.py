"""Unit tests for operations on a single project."""

import contextlib
import logging
import os
import pathlib
import tempfile
import unittest
import unittest.mock

import boilerplates.git_repo_tests
import git
import readchar

from ingit.project import Project

_HERE = pathlib.Path(__file__).resolve().parent

_REMOTE = str(_HERE.parent.joinpath('.git'))

_LOG = logging.getLogger(__name__)


class Tests(boilerplates.git_repo_tests.GitRepoTests):
    # pylint: disable = too-many-public-methods

    def setUp(self):
        super().setUp()
        self.default_branch_name = git.GitConfigParser(
            read_only=True).get_value('init', 'defaultBranch', default='master')

    def test_example(self):
        project = Project('example', ['tag1', 'tag2'], self.repo_path, {})
        self.assertEqual(project.name, 'example')
        self.assertSetEqual(project.tags, {'tag1', 'tag2'})

    def test_clone(self):
        project = Project('example', [], self.repo_path.joinpath('example'), {'origin': _REMOTE})
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            project.clone()
        self.assertTrue(self.repo_path.joinpath('example', '.git').is_dir())

    def test_clone_to_existing_empty_dir(self):
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        self.assertTrue(self.repo_path.exists())
        self.assertFalse(self.repo_path.joinpath('.git').exists())
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            project.clone()
        self.assertTrue(self.repo_path.joinpath('.git').is_dir())

    def test_clone_initialized(self):
        self.git_init()
        project = Project('example', [], self.repo_path, {})
        project.clone()

    def test_clone_no_remote(self):
        project = Project('example', [], self.repo_path.joinpath('example'), {})
        with self.assertRaises(ValueError):
            project.clone()

    def test_clone_nonexisting(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexisting_path = pathlib.Path(temp_dir)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = pathlib.Path(temp_dir)
            project = Project('example', [], path, {'origin': str(nonexisting_path)})
            self.assertTrue(path.is_dir())
            with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
                with self.assertRaises(ValueError):
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

    def test_link_repo_invalid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = pathlib.Path(temp_dir)
            self.assertTrue(path.is_dir())
            project = Project('example', [], path, {})
            with self.assertRaises(RuntimeError):
                project.link_repo()
        self.assertFalse(path.exists())
        project = Project('example', [], path, {})
        with self.assertRaises(RuntimeError):
            project.link_repo()

    # def test_fetch(self):
    #    pass

    # def test_fetch_all(self):
    #    pass

    # def test_checkout(self):
    #    pass

    def test_checkout_case_sensitive_no(self):
        self.git_init()
        self.git_commit_new_file()
        for i in range(0, 88):
            self.repo.git.branch(f'branch_{i:02}')
        project = Project('example', [], self.repo_path, {})
        project.link_repo()
        with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
            project.checkout()

        def readchar_once():
            readchar_once.called_count += 1
            if readchar_once.called_count > 1:
                self.assertLessEqual(readchar_once.called_count, 2)
                raise TimeoutError
            return 'N'
        readchar_once.called_count = 0
        with unittest.mock.patch.object(readchar, 'readchar', readchar_once):
            with self.assertRaises(TimeoutError):
                project.checkout()

    def test_checkout_too_many_branches(self):
        self.git_init()
        self.git_commit_new_file()
        project = Project('example', [], self.repo_path, {})
        project.link_repo()
        for i in range(0, 88):
            self.repo.git.branch(f'branch_{i:02}')
            project.repo.refresh()
            with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
                with open(os.devnull, 'a', encoding='utf-8') as devnull:
                    with contextlib.redirect_stdout(devnull):
                        project.checkout()
        self.repo.git.branch('devel')
        project.repo.refresh()
        with self.assertRaises(RuntimeError):
            with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
                project.checkout()

    # @unittest.expectedFailure
    # def test_merge(self):
    #    pass

    def test_push(self):
        separate_repo = boilerplates.git_repo_tests.GitRepoTests()
        separate_repo.setUp()
        separate_repo.git_init()
        separate_repo.git_commit_new_file()
        separate_repo.repo.git.checkout('-b', 'devel')
        separate_repo.repo.git.branch('-d', self.default_branch_name)
        target_url = str(separate_repo.repo_path)

        self.git_init()
        self.repo.git.remote('add', 'target', target_url)
        project = Project('example', [], self.repo_path, {'target': target_url})
        project.push()
        # project.push(all_branches=True)

        self.git_commit_new_file()
        self.repo.git.push('target', self.default_branch_name)
        self.git_commit_new_file()
        project.repo.refresh()
        self.assertEqual(project.repo.active_branch, self.default_branch_name)
        self.assertIsNone(project.repo.tracking_branches[self.default_branch_name])
        project.push()
        # project.push(all_branches=True)

        self.repo.git.branch(
            self.default_branch_name, set_upstream_to=f'target/{self.default_branch_name}')
        project.repo.refresh()
        self.assertEqual(project.repo.active_branch, self.default_branch_name)
        self.assertTupleEqual(
            project.repo.tracking_branches[self.default_branch_name][:2],
            ('target', self.default_branch_name))
        project.push()
        # project.push(all_branches=True)

        project.repo.refresh()

        separate_repo.tearDown()

    # def test_gc(self):
    #    pass

    def test_status(self):
        self.git_init()
        self.repo.git.remote('add', 'origin', _REMOTE)
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        project.status()
        project.status(ignored=True)

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
        project.status(ignored=True)

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
        with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
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

    def test_status_tracking_branch_gone(self):
        # create 1st repo
        self.git_init()
        self.git_commit_new_file()
        self.repo.git.checkout('-b', 'temporary_branch')
        self.git_commit_new_file()
        with tempfile.TemporaryDirectory() as temp_dir:
            # create 2nd repo by cloning the 1st
            path = pathlib.Path(temp_dir)
            cloned_repo = git.Repo.clone_from(self.repo_path, path, origin='source')
            project = Project('example', [], path, {'source': str(self.repo_path)})
            _LOG.debug('linking repo at %s', path)
            project.link_repo()
            project.status()
            # delete the branch in the 1st repo
            self.repo.git.checkout(self.default_branch_name)
            self.repo.git.branch('-D', 'temporary_branch')
            # fetch the changes
            cloned_repo.git.fetch(prune=True)
            _LOG.debug('refreshing repo at %s', path)
            project.repo.refresh()
            output = cloned_repo.git.branch('-vav')
            _LOG.debug('git branch -vav output:\n%s', output)
            self.assertIn('[source/temporary_branch: gone]', output)
            project.status()

    def test_status_bad_remote(self):
        self.git_init()
        self.repo.git.remote('add', 'mirror', _REMOTE)
        project = Project('example', [], self.repo_path, {'origin': _REMOTE})
        with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
            project.status()
        self.assertNotIn('origin', self.repo.git.remote(v=True))
        self.assertIn(_REMOTE, self.repo.git.remote(v=True))
