"""Single project."""

import collections
import logging
import pathlib

import git

from .json_config import normalize_path
from .repo_data import RepoData
from .action_progress import ActionProgress
from .runtime_interface import ask
from .fetch_flags import create_fetch_info_strings

_LOG = logging.getLogger(__name__)


def normalize_url(url: str):
    return normalize_path(url)


class Project:

    """Single project."""

    def __init__(self, name, tags: set, path: pathlib.Path, remotes: collections.OrderedDict):
        self.name = name
        self.tags = {tag for tag in tags}
        self.path = path
        self.remotes = collections.OrderedDict([(k, v) for k, v in remotes.items()])

        self.repo = None

    @property
    def is_existing(self) -> bool:
        """True if this project's working directory exists."""
        return self.path.is_dir()

    @property
    def is_project_dir_current(self) -> bool:
        """True if current working directory is this project's working directory."""
        return self.is_existing and self.path == pathlib.Path.cwd()

    @property
    def has_git_folder(self) -> bool:
        """True if repo has .git folder."""
        return self.path.joinpath('.git').is_dir()

    @property
    def has_git_file(self) -> bool:
        """True if repo has .git file."""
        return self.path.joinpath('.git').is_file()

    @property
    def has_git_folder_or_file(self) -> bool:
        """True if repo has .git folder or it has .git file."""
        return self.has_git_folder or self.has_git_file

    @property
    def is_initialised(self) -> bool:
        """True if repo exists."""
        return self.is_existing and self.has_git_folder_or_file

    def link_repo(self):
        self.repo = RepoData(git.Repo(normalize_path(str(self.path))))

    def clone(self) -> None:
        """Execute "git clone --recursive --orign <remote-name> <remote-url> <path>".

        All of the <...> values are taken from project configuration.
        Values of <remote-...> are taken from default remote.

        This is followed by "git remote add <remote-name> <remote-url>" for all additional
        configured remotes.
        """
        if self.is_initialised:
            print('repo {} already initialised'.format(self.path))
            return
        if self.is_existing:
            raise ValueError('directory already exists... please check, delete it, and try again')

        remotes_iter = iter(self.remotes.items())
        remote_name, remote_url = next(remotes_iter)

        if ask('Execute "git clone {} --recursive --origin={} {}"?'
               .format(remote_url, remote_name, self.path)) != 'y':
            print('skipping {}'.format(self.path))
            return

        try:
            progress = ActionProgress()
            self.repo = RepoData(git.Repo.clone_from(
                normalize_url(remote_url), normalize_path(str(self.path)), recursive=True,
                origin=remote_name, progress=progress))
            progress.finalize()
        except git.GitCommandError as err:
            raise ValueError('error while cloning "{}" into "{}"'
                             .format(remote_url, self.path)) from err

        for remote_name, remote_url in remotes_iter:
            self.repo.git.remote('add', remote_name, normalize_url(remote_url))

        if len(self.remotes) >= 2:
            self.fetch(all_remotes=True)

    def init(self) -> None:
        """Execute "git init".

        This is followed by "git remote add <remote-name> <remote-url>" for each configured remote.
        """
        if self.is_initialised:
            print('repo {} already initialised'.format(self.path))
            return
        if self.is_existing:
            raise ValueError('directory already exists... please check, delete it, and try again')

        if ask('Execute "git init {}"?'.format(self.path)) != 'y':
            print('skipping {}'.format(self.path))
            return

        self.repo = RepoData(git.Repo.init(normalize_path(str(self.path))))

        for remote_name, remote_url in self.remotes.items():
            self.repo.git.remote('add', remote_name, normalize_url(remote_url))

    def fetch(self, all_remotes: bool = False) -> None:
        """Execute "git fetch --prune" on a remote of trancking branch of current branch.

        Or execute "git fetch --prune" for all remotes.
        """
        if not self.is_existing:
            print('skipping non-existing {}'.format(self.path))
            return
        if self.repo is None:
            self.link_repo()
        self.repo.refresh()
        # fetch_info = self.repo.git.fetch(all=all_remotes)
        if all_remotes:
            remote_names = self.repo.remotes
        else:
            branch = str(self.repo._repo.active_branch)
            try:
                remote_name, _ = self.repo.tracking_branches[branch]
                remote_names = [remote_name]
            except KeyError:
                _LOG.warning('branch "%s" not configured, fetching all remotes', branch)
                remote_names = self.repo.remotes
            except TypeError:
                _LOG.warning('current branch "%s" has no tracking branch, fetching all remotes',
                             branch)
                remote_names = self.repo.remotes

        for remote_name in remote_names:
            fetch_infos = self._fetch_single_remote(remote_name)
            if not fetch_infos:
                _LOG.warning('no fetch info after fetching from remote "%s" in "%s"',
                             remote_name, self.name)
            for fetch_info in fetch_infos:
                merge = self._interpret_fetch_info(fetch_info)
                if merge:
                    raise NotImplementedError('merging not yet implemented')

    def _fetch_single_remote(self, remote_name: str):
        try:
            progress = ActionProgress()
            fetch_infos = self.repo.remotes[remote_name].fetch(prune=True, progress=progress)
            progress.finalize()
        except git.GitCommandError as err:
            raise ValueError('error while fetching remote "{}" in "{}"'
                             .format(remote_name, self.name)) from err
        return fetch_infos

    def _interpret_fetch_info(self, fetch_info) -> bool:
        info_strings, prefix = create_fetch_info_strings(fetch_info)
        if info_strings:
            print('{} fetched "{}" in "{}"; {}'.format(
                prefix, fetch_info.ref, self.name, ', '.join(info_strings)))
        if not fetch_info.flags & fetch_info.FAST_FORWARD:
            return False
        ans = ask('The fetch was fast-forward. Do you want to merge?')
        return ans == 'y'

    def checkout(self) -> None:
        """Interactively select revision and execute "git checkout <revision>" on it.

        The list of branches to select from is composed by combinig:
        - local branches
        - local tags
        - branches on all remotes
        """
        if not self.is_existing:
            print('skipping non-existing {}'.format(self.path))
            return
        if self.repo is None:
            self.link_repo()
        self.repo.refresh()

        # if self.is_on_only_branch():
        #    return

        revisions = collections.OrderedDict()

        keys = '1234567890abcdefghijklmopqrstuvwxz'
        index = 0
        for branch in self.repo.branches:
            revisions[keys[index]] = (branch, None)
            index += 1

        for tag in self.repo._repo.tags:
            revisions[keys[index]] = (tag, 'tag')
            index += 1

        special_branches = {'HEAD', 'FETCH_HEAD'}
        remote_tracking_branches = set(self.repo.tracking_branches.values())

        for (remote, branch) in self.repo.remote_branches:
            # remote_branch = '{}/{}'.format(remote, branch)
            if (remote, branch) in remote_tracking_branches \
                    or branch in special_branches:
                continue
            to_checkout = branch if branch not in self.repo.branches else '{}/{}'.format(remote, branch)
            revisions[keys[index]] = (to_checkout, 'based on {}'.format(remote))
            index += 1

        active_branch = self.repo._repo.active_branch
        if active_branch is None:
            revisions['n'] = ('---', 'keep no branch/tag')
        else:
            active_branch = str(active_branch)
            # assert revisions['1'][0] == active_branch
            for key, (revision, comment) in revisions.items():
                if revision == active_branch:
                    _ = 'no change'
                    comment = '{}, {}'.format(comment, _) if comment else _
                    revisions[key] = (revision, comment)
                    break

        print('Checkout options:')
        for key, (revision, comment) in revisions.items():
            if comment is None:
                print('  {}: {}'.format(key, revision))
            else:
                print('  {}: {} ({})'.format(key, revision, comment))

        answer = ask('Which branch to checkout?', answers=[key for key in keys[:index]] + ['n'])
        if answer == 'n':
            return
        target, _ = revisions[answer]
        if target == active_branch:
            return

        self.repo.git.checkout(target)

    def merge(self) -> None:
        """Execute "git merge" for current branch."""
        if not self.is_existing:
            print('skipping non-existing {}'.format(self.path))
            return
        if self.repo is None:
            self.link_repo()
        raise NotImplementedError('merging not yet implemented')

    def push(self, all_branches: bool = False) -> None:
        """Push current branch to it's tracking branch.

        Or, push all local branches to their tracking branches.
        """
        if not self.is_existing:
            print('skipping non-existing {}'.format(self.path))
            return
        if self.repo is None:
            self.link_repo()
        raise NotImplementedError()

    def collect_garbage(self) -> None:
        """Execute "git gc --agressive --prune"."""
        if not self.is_existing:
            print('skipping non-existing {}'.format(self.path))
            return
        if self.repo is None:
            self.link_repo()

        try:
            self.repo.git.gc(aggressive=True, prune=True)
        except git.GitCommandError as err:
            raise ValueError('error while collecting garbage in "{}"'.format(self.path)) from err

    def status(self) -> None:
        """Execute "git status --short" and run "git gui" if there is any output."""
        if not self.is_existing:
            print('skipping non-existing {}'.format(self.path))
            return
        if self.repo is None:
            self.link_repo()

        try:
            status_log = self.repo.git.status(short=True).splitlines()
        except git.GitCommandError as err:
            raise ValueError('error while getting status of "{}"'.format(self.path)) from err

        if status_log:
            print('!! unclear status in "{}":'.format(self.path))
            for line in status_log:
                print(line)

        self.repo.refresh()
