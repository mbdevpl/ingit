"""Single project."""

import collections
import pathlib

import git

from .json_config import normalize_path
from .repo_data import RepoData
from .action_progress import ActionProgress
from .runtime_interface import ask


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
        self.repo = RepoData(git.Repo(str(self.path)))

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
        """Execute "git fetch", or "git fetch --all"."""
        if self.repo is None:
            self.link_repo()
        self.repo.git.fetch(all=all_remotes)

    def checkout(self) -> None:
        """Interactively select revision and execute "git checkout <revision>" on it.

        The list of branches to select from is composed by combinig:
        - local branches
        - local tags
        - branches on all remotes
        """

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
            remote_branch = '{}/{}'.format(remote, branch)
            if remote_branch in remote_tracking_branches \
                    or branch in special_branches:
                continue
            to_checkout = branch if branch not in self.repo.branches else remote_branch
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
        if self.repo is None:
            self.link_repo()
        raise NotImplementedError()

    def push(self) -> None:
        if self.repo is None:
            self.link_repo()
        raise NotImplementedError()

    def collect_garbage(self) -> None:
        """Execute "git gc --agressive --prune"."""
        if self.repo is None:
            self.link_repo()

        try:
            self.repo.git.gc(aggressive=True, prune=True)
        except git.GitCommandError as err:
            raise ValueError('error while collecting garbage in "{}"'.format(self.path)) from err

    def status(self) -> None:
        """Execute "git status --short" and run "git gui" if there is any output."""
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
