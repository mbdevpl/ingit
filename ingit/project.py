"""Single project."""

import collections
import logging
import pathlib
import typing as t

import git

from .json_config import normalize_path
from .repo_data import RepoData
from .action_progress import ActionProgress
from .runtime_interface import ask
from .fetch_flags import create_fetch_info_strings

_LOG = logging.getLogger(__name__)

OUT = logging.getLogger('ingit.interface.print')


def normalize_url(url: str):
    return normalize_path(url)


class Project:

    """Single project."""

    def __init__(self, name: str, tags: t.Iterable[str], path: pathlib.Path,
                 remotes: t.Mapping[str, str]):
        assert isinstance(name, str), type(name)
        assert isinstance(tags, collections.abc.Iterable), type(tags)
        assert isinstance(path, pathlib.Path), type(path)
        assert isinstance(remotes, collections.abc.Mapping), type(remotes)
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
            OUT.info('repo {} already initialised'.format(self.path))
            return
        if self.is_existing:
            raise ValueError('directory already exists... please check, delete it, and try again')

        remotes_iter = iter(self.remotes.items())
        remote_name, remote_url = next(remotes_iter)

        if ask('Execute "git clone {} --recursive --origin={} {}"?'
               .format(remote_url, remote_name, self.path)) != 'y':
            OUT.warning('skipping {}'.format(self.path))
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
            OUT.error('repo {} already initialised'.format(self.path))
            return
        if self.is_existing:
            raise ValueError('directory already exists... please check, delete it, and try again')

        if ask('Execute "git init {}"?'.format(self.path)) != 'y':
            OUT.warning('skipping {}'.format(self.path))
            return

        self.repo = RepoData(git.Repo.init(normalize_path(str(self.path))))

        for remote_name, remote_url in self.remotes.items():
            self.repo.git.remote('add', remote_name, normalize_url(remote_url))

    def fetch(self, all_remotes: bool = False) -> None:
        """Execute "git fetch --prune" on a remote of trancking branch of current branch.

        Or execute "git fetch --prune" for all remotes.
        """
        if not self.is_existing:
            OUT.info('skipping non-existing "%s"...', self.path)
            return
        if self.repo is None:
            self.link_repo()
        self.repo.refresh()

        if all_remotes:
            remote_names = self.repo.remotes
        else:
            remote_names = self._determine_remotes_to_fetch()

        for remote_name in remote_names:
            fetch_infos = self._fetch_single_remote(remote_name)
            if not fetch_infos:
                _LOG.warning('no fetch info after fetching from remote "%s" in "%s"',
                             remote_name, self.name)
            for fetch_info in fetch_infos:
                self._print_fetch_info(fetch_info)
                if fetch_info.flags & fetch_info.FAST_FORWARD:
                    # ans = ask('The fetch was fast-forward. Do you want to merge?')
                    # if ans == 'y':
                    #    raise NotImplementedError('merging not yet implemented')
                    pass

    def _determine_remotes_to_fetch(self):
        if self.repo.active_branch is None:
            OUT.warning('!! "%s" is not on any branch, fetching all remotes', self.path)
            return self.repo.remotes
        try:
            remote_name, _ = self.repo.tracking_branches[self.repo.active_branch]
        except KeyError:
            _LOG.warning('branch "%s" in "%s" not configured, fetching all remotes',
                         self.repo.active_branch, self.path)
            return self.repo.remotes
        except TypeError:
            OUT.warning('!! branch "%s" in "%s" has no tracking branch, fetching all remotes',
                        self.repo.active_branch, self.path)
            return self.repo.remotes
        return [remote_name]

    def _fetch_single_remote(self, remote_name: str):
        try:
            progress = ActionProgress()
            fetch_infos = self.repo.remotes[remote_name].fetch(prune=True, progress=progress)
            progress.finalize()
        except git.GitCommandError as err:
            raise ValueError('error while fetching remote "{}" ("{}") in "{}"'.format(
                remote_name, self.repo.remotes[remote_name].url, self.name)) from err
        return fetch_infos

    def _print_fetch_info(self, fetch_info) -> bool:
        info_strings, prefix = create_fetch_info_strings(fetch_info)
        if not info_strings:
            return
        level = logging.WARNING if fetch_info.flags & fetch_info.HEAD_UPTODATE \
            else logging.CRITICAL
        OUT.log(level, '{} fetched "{}" in "{}"; {}'.format(
            prefix, fetch_info.ref, self.name, ', '.join(info_strings)))

    def checkout(self) -> None:
        """Interactively select revision and execute "git checkout <revision>" on it.

        The list of branches to select from is composed by combinig:
        - local branches
        - local tags
        - branches on all remotes
        """
        if not self.is_existing:
            OUT.info('skipping non-existing "%s"...', self.path)
            return
        if self.repo is None:
            self.link_repo()
        self.repo.refresh()

        # if self.is_on_only_branch():
        #    return

        keys = '1234567890abcdefghijklmopqrstuvwxz'
        revisions = self._prepare_checkout_list(keys)

        print('Checkout options:')
        for key, (revision, comment) in revisions.items():
            if comment is None:
                print('  {}: {}'.format(key, revision))
            else:
                print('  {}: {} ({})'.format(key, revision, comment))

        answer = ask('Which branch to checkout?',
                     answers=[key for key in keys[:len(revisions)]] + ['n'])
        if answer == 'n':
            return
        target, _ = revisions[answer]
        if target == self.repo.active_branch:
            return

        self.repo.git.checkout(target)

    def _prepare_checkout_list(self, keys: str):
        revisions = collections.OrderedDict()

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
            if branch in self.repo.branches:
                to_checkout = '{}/{}'.format(remote, branch)
            else:
                to_checkout = branch
            revisions[keys[index]] = (to_checkout, 'based on {}'.format(remote))
            index += 1

        if self.repo.active_branch is None:
            revisions['n'] = ('---', 'keep no branch/tag')
        else:
            # assert revisions['1'][0] == active_branch
            for key, (revision, comment) in revisions.items():
                if revision == self.repo.active_branch:
                    _ = 'no change'
                    comment = '{}, {}'.format(comment, _) if comment else _
                    revisions[key] = (revision, comment)
                    break

        return revisions

    def merge(self) -> None:
        """Execute "git merge" for current branch."""
        if not self.is_existing:
            OUT.info('skipping non-existing "%s"...', self.path)
            return
        if self.repo is None:
            self.link_repo()
        raise NotImplementedError('merging not yet implemented')

    def push(self, all_branches: bool = False) -> None:
        """Push current branch to it's tracking branch.

        Or, push all local branches to their tracking branches.
        """
        if not self.is_existing:
            OUT.info('skipping non-existing "%s"...', self.path)
            return
        if self.repo is None:
            self.link_repo()
        raise NotImplementedError('pushing not yet implemented')

    def collect_garbage(self) -> None:
        """Execute "git gc --agressive --prune"."""
        if not self.is_existing:
            OUT.info('skipping non-existing "%s"...', self.path)
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
            OUT.info('skipping non-existing "%s"...', self.path)
            return
        if self.repo is None:
            self.link_repo()

        try:
            status_log = self.repo.git.status(short=True).splitlines()
        except git.GitCommandError as err:
            raise ValueError('error while getting status of "{}"'.format(self.path)) from err

        if status_log:
            OUT.critical('!! unclear status in "{}":'.format(self.path))
            for line in status_log:
                OUT.critical(line)

        self.repo.refresh()
        self._status_branch()
        self._status_remotes()

    def _get_log(self, start_ref: str, end_ref: str) -> str:
        """Get log as if start_ref..end_ref was used."""
        refs = '{}..{}'.format(start_ref, end_ref)
        # return self.repo.git.log('--pretty=oneline', refs, color='always').splitlines()
        return self.repo.git.log('--color=always', '--pretty=oneline', refs).splitlines()

    def _print_log(self, ref_log, printed_header: str = '', head_count: int = 10,
                   tail_count: int = 10) -> None:
        if printed_header:
            OUT.critical(printed_header)
        if len(ref_log) > head_count + tail_count + 1:
            for line in ref_log[:head_count]:
                OUT.critical(line)
            OUT.critical(
                '... skipped {} commits'.format(len(ref_log) - head_count - tail_count))
            for line in ref_log[-tail_count:]:
                OUT.critical(line)
        else:
            for line in ref_log:
                OUT.critical(line)

    def _status_branch(self, branch: str = None) -> None:
        """Evaluate the status of single branch by comparing it to the remote branch.

        auto-answers used in this function: create_remote_branch, push, merge, forget_locally
        """
        if branch is None:
            branch = self.repo.active_branch
        if branch is None:
            OUT.warning('cannot diagnose branch status in "%s" -- not on any branch', self.path)
            return
        tracking_branch_data = self.repo.tracking_branches[branch]
        if tracking_branch_data is None:
            OUT.warning('cannot diagnose branch status in "%s"'
                        ' -- current branch has no tracking branch', self.path)
            return
        tracking_branch = '/'.join(tracking_branch_data)
        not_pushed_log = self._get_log(tracking_branch, branch)
        if not_pushed_log:
            self._print_log(not_pushed_log, '!! not pushed commits from "{}" to "{}" in "{}":'
                            .format(branch, tracking_branch, self.path))
            # self.push_single_remote(
            #    tracking_branch_data[0], ['{0}:{0}'.format(branch, tracking_branch_data[1])])
        not_merged_log = self._get_log(branch, tracking_branch)
        if not_merged_log:
            self._print_log(not_pushed_log, '!! not merged commits from "{}" to "{}" in "{}":'
                            .format(tracking_branch, branch, self.path))
            '''
            answer = self.interface.get_answer('merge')
            if answer in ['y', 'm']:
                self.merge_single_branch(remote, branch)
            elif answer == 'b':
                self.rebase_single_branch(remote, branch)
            elif answer == 'r':
                self.hard_reset_single_branch(remote, branch)
            elif self.interface.confirm('forget_locally'):
                self.repo.git.update_ref('refs/remotes/{0}/{1}'.format(remote, branch), branch)
            '''

    def _status_remotes(self):
        remotes_in_config = set(self.remotes)
        remotes = set(self.repo.remotes)
        extra_remotes = remotes - remotes_in_config
        missing_remotes = remotes_in_config - remotes
        if extra_remotes or missing_remotes:
            OUT.critical('!! repo "%s" has different remotes than it should', self.path)
            for extra_remote in extra_remotes:
                OUT.critical('!! extra remote: "%s"', extra_remote)
            for missing_remote in missing_remotes:
                OUT.critical('!! missing remote: "%s"', missing_remote)
                if extra_remotes:
                    # TODO: check extra remotes for identical urls
                    continue
                ans = ask('Add remote "{}" with url "{}"?'
                          .format(missing_remote, self.remotes[missing_remote]))
                if ans == 'y':
                    self.repo.git.remote('add', missing_remote, self.remotes[missing_remote])

    def __str__(self):
        fields = ['path="{}"'.format(self.path)]
        if not self.is_initialised:
            if not self.is_existing:
                fields.append('not existing')
            else:
                fields.append('not initialized')
        if self.tags:
            fields.append('tags={}'.format(self.tags))
        return '{} ({})'.format(self.name, ', '.join(fields))
