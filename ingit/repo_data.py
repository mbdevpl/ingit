"""Git repository data gathering and validation."""

import collections
import logging
import pathlib
import typing as t

import git

_LOG = logging.getLogger(__name__)


TrackingBranchTuple = t.NamedTuple('TrackingBranchTuple', [
    ('remote_name', str),
    ('tracking_branch_name', str),
    ('reference', git.Reference),
])


class RepoData:
    """Gather and validate data of a git repository."""

    def __init__(self, repo: git.Repo):
        assert isinstance(repo, git.Repo), type(repo)
        self._repo = repo
        self.remotes: t.Mapping[str, git.Remote] = {}
        self.branches: t.Mapping[str, git.Reference] = {}
        self._active_branch: t.Optional[str] = None
        self.remote_branches: t.Mapping[t.Tuple[str, str], git.Reference] = {}
        self.tracking_branches: t.Mapping[str, t.Optional[TrackingBranchTuple]] = {}

    @property
    def active_branch(self) -> t.Optional[str]:
        return self._active_branch

    @active_branch.setter
    def active_branch(self, branch_name: t.Optional[str]) -> None:
        self._active_branch = branch_name
        if branch_name is None:
            return
        try:
            self._repo.active_branch.tracking_branch()
        except AttributeError:
            _LOG.warning('current branch "%s" in %s has no tracking branch',
                         self._active_branch, self._repo)

    @property
    def current_tracking_branch(self) -> t.Optional[str]:
        """Get the tracking branch of the current branch, if any."""
        if self._active_branch is None:
            return None
        tracking_branch = self.tracking_branches[self._active_branch]
        if tracking_branch is None:
            return None
        return f'{tracking_branch.remote_name}/{tracking_branch.tracking_branch_name}'

    def _refresh_tracking_branches(self) -> None:
        _tracking_branches: t.Dict[str, t.Optional[TrackingBranchTuple]] = {}
        for name, ref in self.branches.items():
            _tracking_branch = ref.tracking_branch()
            if _tracking_branch is None:
                _tracking_branches[name] = None
                continue
            assert isinstance(_tracking_branch, git.Reference), type(_tracking_branch)
            remote_name, _, branch_name = str(_tracking_branch).partition('/')
            _tracking_branches[name] = TrackingBranchTuple(
                remote_name, branch_name, _tracking_branch)
        self.tracking_branches = _tracking_branches

    @property
    def default_remote(self) -> t.Optional[str]:
        """Get the default remote name.

        Default remote name would be the remote name of the tracking branch of the current branch.
        It's None if the current branch has no tracking branch, or if there's no current branch.
        """
        if self.current_tracking_branch is None:
            return None
        assert self._active_branch is not None
        tracking_branch = self.tracking_branches[self._active_branch]
        assert tracking_branch is not None
        return tracking_branch.remote_name

    def _find_default_remote_ref(self) -> t.Optional[git.Remote]:
        default_remote = self.default_remote
        if default_remote is None:
            return None
        matching_remotes = [_ for _ in self._repo.remotes if str(_) == default_remote]
        assert len(matching_remotes) <= 1, matching_remotes
        if not matching_remotes:
            return None
        return matching_remotes[0]

    def _refresh_remotes(self) -> None:
        default_remote = self.default_remote
        default_remote_ref = self._find_default_remote_ref()
        if default_remote is None:
            self.remotes = collections.OrderedDict([])
        else:
            assert default_remote_ref is not None, default_remote
            self.remotes = collections.OrderedDict([(default_remote, default_remote_ref)])
        self.remotes.update(collections.OrderedDict([(str(_), _) for _ in self._repo.remotes]))

    def refresh(self) -> None:
        """Refresh repository data."""
        self.active_branch = None
        try:
            if self._repo.branches:
                self.active_branch = str(self._repo.active_branch)
        except TypeError:
            _LOG.warning('repository %s is not on any branch', self._repo)

        self.branches = collections.OrderedDict(
            [] if self._active_branch is None
            else [(self._active_branch, self._repo.active_branch)])
        self.branches.update(collections.OrderedDict([(str(_), _) for _ in self._repo.branches]))
        assert all(_ is not None for name, _ in self.branches.items()), (self._repo, self.branches)
        self._refresh_tracking_branches()
        self._refresh_remotes()

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

    @property
    def tags(self):
        return self._repo.tags

    @property
    def git(self):
        return self._repo.git
