"""Git repository data gathering and validation."""

import collections
import logging
import pathlib
import typing as t

import git

_LOG = logging.getLogger(__name__)


class RepoData:
    """Gather and validate data of a git repository."""

    def __init__(self, repo: git.Repo):
        assert isinstance(repo, git.Repo), type(repo)
        self._repo = repo
        self.remotes: t.Mapping[str, git.Remote] = {}
        self.branches: t.Mapping[str, git.Reference] = {}
        self._active_branch: t.Optional[str] = None
        self._current_tracking_branch: t.Optional[str] = None
        self.remote_branches: t.Mapping[str, git.Reference] = {}
        self.tracking_branches: t.Mapping[str, git.Reference] = {}

    @property
    def git(self):
        return self._repo.git

    @property
    def active_branch(self) -> t.Optional[str]:
        return self._active_branch

    @active_branch.setter
    def active_branch(self, branch_name: t.Optional[str]) -> None:
        self._active_branch = branch_name
        self._current_tracking_branch = None
        if branch_name is None:
            return
        current_tracking_ref = None
        try:
            current_tracking_ref = self._repo.active_branch.tracking_branch()
        except AttributeError:
            _LOG.warning('current branch "%s" in %s has no tracking branch',
                         self._active_branch, self._repo)
        if current_tracking_ref is not None:
            self._current_tracking_branch = str(current_tracking_ref)

    @property
    def current_tracking_branch(self) -> t.Optional[str]:
        """Get the tracking branch of the current branch, if any."""
        return self._current_tracking_branch

    @property
    def default_remote(self) -> t.Optional[str]:
        """Get the default remote name.

        Default remote name would be the remote name of the tracking branch of the current branch.
        It's None if the current branch has no tracking branch, or if there's no current branch.
        """
        if self._current_tracking_branch is None:
            return None
        return self._current_tracking_branch.partition('/')[0]

    def refresh(self) -> None:
        """Refresh repository data."""
        self.active_branch = None
        try:
            if self._repo.branches:
                self.active_branch = str(self._repo.active_branch)
        except TypeError:
            _LOG.warning('repository %s is not on any branch', self._repo)

        self.branches = collections.OrderedDict([] if self._active_branch is None
                                                else [(self._active_branch, None)])
        self.branches.update(collections.OrderedDict([(str(_), _) for _ in self._repo.branches]))
        assert all(_ is not None for name, _ in self.branches.items()), (self._repo, self.branches)

        self.tracking_branches = {
            name: (tuple(str(_.tracking_branch()).partition('/')[::2])
                   if _.tracking_branch() else None)
            for name, _ in self.branches.items()}

        default_remote = self.default_remote
        self.remotes = collections.OrderedDict([] if default_remote is None
                                               else [(default_remote, None)])
        self.remotes.update(collections.OrderedDict([(str(_), _) for _ in self._repo.remotes]))

        self.remote_branches = {
            (remote_name, str(_).replace(f'{remote_name}/', '')): _
            for remote_name, remote in self.remotes.items() for _ in remote.refs}

    def generate_repo_configuration(self) -> t.Dict[str, t.Any]:
        assert self._repo.working_tree_dir is not None
        path = pathlib.Path(self._repo.working_tree_dir)
        return {
            'name': path.name,
            'path': str(path.resolve()),
            'remotes': collections.OrderedDict(
                [(name, remote.url) for name, remote in self.remotes.items()]),
            'tags': []}

    def __str__(self):
        return f'{self._repo}:(branches={self.tracking_branches},remotes={self.remotes})'
