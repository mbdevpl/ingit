"""Unit tests for git repository data gathering."""

import logging

import boilerplates.git_repo_tests
import git

from ingit.repo_data import RepoData

_LOG = logging.getLogger(__name__)


class Tests(boilerplates.git_repo_tests.GitRepoTests):

    def setUp(self):
        super().setUp()
        self.default_branch_name = git.GitConfigParser(
            read_only=True).get_value('init', 'defaultBranch')

    def test_empty_repo(self):
        self.git_init()
        repo = RepoData(self.repo)
        repo.refresh()
        self.assertDictEqual(repo.remotes, {})
        self.assertDictEqual(repo.branches, {})
        self.assertEqual(repo.active_branch, None)
        self.assertDictEqual(repo.remote_branches, {})
        self.assertDictEqual(repo.tracking_branches, {})

    def test_detached_head(self):
        self.git_init()
        self.git_commit_new_file()
        self.repo.git.checkout(self.repo_head_hexsha)
        repo = RepoData(self.repo)
        repo.refresh()
        self.assertDictEqual(repo.remotes, {})
        self.assertSetEqual(set(repo.branches), {self.default_branch_name})
        self.assertEqual(repo.active_branch, None)
        self.assertDictEqual(repo.remote_branches, {})
        self.assertSetEqual(set(repo.tracking_branches), {self.default_branch_name})

    def test_no_remotes(self):
        self.git_init()
        self.git_commit_new_file()
        repo = RepoData(self.repo)
        repo.refresh()
        self.assertDictEqual(repo.remotes, {})
        self.assertSetEqual(set(repo.branches), {self.default_branch_name})
        self.assertEqual(repo.active_branch, self.default_branch_name)
        self.assertDictEqual(repo.remote_branches, {})
        self.assertSetEqual(set(repo.tracking_branches), {self.default_branch_name})
