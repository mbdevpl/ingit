"""Unit tests for git repository data gathering."""

import logging
import tempfile

import boilerplates.git_repo_tests
import git

from ingit.repo_data import RepoData

_LOG = logging.getLogger(__name__)


class Tests(boilerplates.git_repo_tests.GitRepoTests):

    def setUp(self):
        super().setUp()
        self.default_branch_name = git.GitConfigParser(
            read_only=True).get_value('init', 'defaultBranch', default='master')

    def test_empty_repo(self):
        self.git_init()
        repo = RepoData(self.repo)
        repo.refresh()
        self.assertDictEqual(repo.remotes, {})
        self.assertIsNone(repo.default_remote)
        self.assertDictEqual(repo.branches, {})
        self.assertIsNone(repo.active_branch)
        self.assertIsNone(repo.current_tracking_branch)
        self.assertDictEqual(repo.remote_branches, {})
        self.assertDictEqual(repo.tracking_branches, {})

    def test_detached_head(self):
        self.git_init()
        self.git_commit_new_file()
        self.repo.git.checkout(self.repo_head_hexsha)
        repo = RepoData(self.repo)
        repo.refresh()
        self.assertDictEqual(repo.remotes, {})
        self.assertIsNone(repo.default_remote)
        self.assertSetEqual(set(repo.branches), {self.default_branch_name})
        self.assertIsNone(repo.active_branch)
        self.assertIsNone(repo.current_tracking_branch)
        self.assertDictEqual(repo.remote_branches, {})
        self.assertSetEqual(set(repo.tracking_branches), {self.default_branch_name})

    def test_no_remotes(self):
        self.git_init()
        self.git_commit_new_file()
        repo = RepoData(self.repo)
        repo.refresh()
        self.assertDictEqual(repo.remotes, {})
        self.assertIsNone(repo.default_remote)
        self.assertSetEqual(set(repo.branches), {self.default_branch_name})
        self.assertEqual(repo.active_branch, self.default_branch_name)
        self.assertIsNone(repo.current_tracking_branch)
        self.assertDictEqual(repo.remote_branches, {})
        self.assertSetEqual(set(repo.tracking_branches), {self.default_branch_name})

    def test_has_remotes(self):
        self.git_init()
        self.git_commit_new_file()
        origin_name = 'my-origin'
        with tempfile.TemporaryDirectory() as tmpdir:
            git_repo = git.Repo.clone_from(self.repo_path, tmpdir, origin=origin_name)
            repo = RepoData(git_repo)
            repo.refresh()
            self.assertGreater(len(repo.remotes), 0)
            self.assertEqual(repo.default_remote, origin_name)
            self.assertSetEqual(set(repo.branches), {self.default_branch_name})
            self.assertEqual(repo.active_branch, self.default_branch_name)
            self.assertEqual(
                repo.current_tracking_branch, f'{origin_name}/{self.default_branch_name}')
            self.assertGreater(len(repo.remote_branches), 0)
            self.assertEqual(len(repo.tracking_branches), 1)
            key, value = next(iter(repo.tracking_branches.items()))
            self.assertEqual(key, self.default_branch_name)
            self.assertEqual(value.remote_name, origin_name)
            self.assertEqual(value.tracking_branch_name, self.default_branch_name)
