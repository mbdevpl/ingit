"""Git repository data gathering and validation."""

import collections
import logging
import pathlib

import git

_LOG = logging.getLogger(__name__)


class RepoData:

    """Gather and validate data of a git repository."""

    def __init__(self, repo: git.Repo):
        assert isinstance(repo, git.Repo), type(repo)
        self._repo = repo
        self.remotes = {}
        self.branches = {}
        self.active_branch = None
        self.remote_branches = {}
        self.tracking_branches = {}

    @property
    def git(self):
        return self._repo.git

    def refresh(self):
        """Refresh repository data."""

        self.active_branch = None
        try:
            if self._repo.branches:
                self.active_branch = str(self._repo.active_branch)
        except TypeError:
            _LOG.warning('repository %s is not on any branch', self._repo)

        current_tracking_branch = None
        default_remote = None
        if self.active_branch is not None:
            try:
                current_tracking_branch = self._repo.active_branch.tracking_branch()
                if current_tracking_branch is not None:
                    current_tracking_branch = str(current_tracking_branch)
                default_remote = current_tracking_branch.partition('/')[0]
            except AttributeError:
                _LOG.warning('current branch "%s" in %s has no tracking branch',
                             self.active_branch, self._repo)

        self.branches = collections.OrderedDict([] if self.active_branch is None
                                                else [(self.active_branch, None)])
        self.branches.update(collections.OrderedDict([(str(_), _) for _ in self._repo.branches]))
        assert all(_ is not None for name, _ in self.branches.items()), (self._repo, self.branches)

        self.tracking_branches = {
            name: (tuple(str(_.tracking_branch()).partition('/')[::2])
                   if _.tracking_branch() else None)
            for name, _ in self.branches.items()}

        self.remotes = collections.OrderedDict([] if default_remote is None
                                               else [(default_remote, None)])
        self.remotes.update(collections.OrderedDict([(str(_), _) for _ in self._repo.remotes]))

        self.remote_branches = {
            (remote_name, str(_).replace('{}/'.format(remote_name), '')): _
            for remote_name, remote in self.remotes.items() for _ in remote.refs}

    def generate_repo_configuration(self):
        path = pathlib.Path(self._repo.working_tree_dir)
        return {
            'name': path.name,
            'path': str(path.resolve()),
            'remotes': collections.OrderedDict(
                [(name, remote.url) for name, remote in self.remotes.items()]),
            'tags': []}

    def __str__(self):
        return '{}:(branches={},remotes={})'.format(
            self._repo, self.tracking_branches, self.remotes)
