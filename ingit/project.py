"""Single project."""

import collections
import pathlib

import git

from .repo_data import RepoData
from .action_progress import ActionProgress


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
        """
        if self.is_initialised:
            raise ValueError('repo {} already initialised'.format(self.path))
        if self.is_existing:
            raise ValueError('directory already exists... please check, delete it, and try again')

        remote_name, remote_url = next(iter(self.remotes.items()))

        try:
            progress = ActionProgress()
            self.repo = RepoData(git.Repo.clone_from(
                remote_url, str(self.path), recursive=True, origin=remote_name, progress=progress))
            progress.finalize()
        except git.GitCommandError as err:
            raise ValueError('error while cloning "{}" into "{}"'
                             .format(remote_url, self.path)) from err

    def init(self) -> None:
        """Execute "git init", followed by "git remote add" for each configured remote."""
        if self.is_initialised:
            raise ValueError('repo {} already initialised'.format(self.path))
        if self.is_existing:
            raise ValueError('directory already exists... please check, delete it, and try again')
        self.repo = RepoData(git.Repo.init(self.path))

        for remote_name, remote_url in self.remotes.items():
            self.repo.git.remote('add', remote_name, remote_url)

    def fetch(self, all_remotes: bool = False) -> None:
        """Execute "git fetch", or "git fetch --all"."""
        if self.repo is None:
            self.link_repo()
        self.repo.git.fetch(all=all_remotes)

    def checkout(self) -> None:
        if self.repo is None:
            self.link_repo()
        raise NotImplementedError()

    def merge(self) -> None:
        if self.repo is None:
            self.link_repo()
        raise NotImplementedError()

    def push(self) -> None:
        if self.repo is None:
            self.link_repo()
        raise NotImplementedError()

    def gc(self) -> None:
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
