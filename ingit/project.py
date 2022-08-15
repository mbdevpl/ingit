"""Single project."""

import collections
import collections.abc
import logging
import pathlib
import typing as t

import git

from .json_config import normalize_path
from .repo_data import RepoData
from .action_progress import ActionProgress
from .runtime_interface import ask
from .fetch_flags import create_fetch_info_strings
from .push_flags import create_push_info_strings

_LOG = logging.getLogger(__name__)

OUT = logging.getLogger('ingit.interface.print')

_SPECIAL_REFS = {'HEAD', 'FETCH_HEAD'}


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
        self.tags = set(tags)
        self.path = path
        self.remotes = collections.OrderedDict(list(remotes.items()))

        self.repo: t.Optional[RepoData] = None

    @property
    def is_existing(self) -> bool:
        """Return True if this project's working directory exists."""
        return self.path.is_dir()

    @property
    def has_git_folder(self) -> bool:
        """Return True if repo has .git folder."""
        return self.path.joinpath('.git').is_dir()

    @property
    def has_git_file(self) -> bool:
        """Return True if repo has .git file."""
        return self.path.joinpath('.git').is_file()

    @property
    def has_git_folder_or_file(self) -> bool:
        """Return True if repo has .git folder or it has .git file."""
        return self.has_git_folder or self.has_git_file

    @property
    def is_initialised(self) -> bool:
        """Return True if repo exists."""
        return self.is_existing and self.has_git_folder_or_file

    def link_repo(self):
        assert self.repo is None, self.repo
        self.repo = RepoData(git.Repo(normalize_path(str(self.path))))

    def clone(self) -> None:
        """Execute "git clone --recursive --origin <remote-name> <remote-url> <path>".

        All of the <...> values are taken from project configuration.
        Values of <remote-...> are taken from default remote.

        This is followed by "git remote add <remote-name> <remote-url>" for all additional
        configured remotes.
        """
        if self.is_initialised:
            OUT.info('repo %s already initialised', self.path)
            return
        if self.is_existing:
            raise ValueError('directory already exists... please check, delete it, and try again')

        remotes = list(self.remotes.items())
        if not remotes:
            raise ValueError(f'no configured remotes in repo {self.path}... cannot clone')
        (remote_name, remote_url), remaning_remotes = remotes[0], remotes[1:]

        if ask(f'Execute "git clone {remote_url} --recursive --origin={remote_name}'
               f' {self.path}"?') != 'y':
            OUT.warning('skipping %s', self.path)
            return

        try:
            progress = ActionProgress()
            self.repo = RepoData(git.Repo.clone_from(
                normalize_url(remote_url), normalize_path(str(self.path)), recursive=True,
                origin=remote_name, progress=progress))
            progress.finalize()
        except git.GitCommandError as err:
            raise ValueError(f'error while cloning "{remote_url}" into "{self.path}"') from err

        for remote_name, remote_url in remaning_remotes:
            self.repo.git.remote('add', remote_name, normalize_url(remote_url))
            self.repo.refresh()
            self._fetch_remote(remote_name)

    def init(self) -> None:
        """Execute "git init".

        This is followed by "git remote add <remote-name> <remote-url>" for each configured remote.
        """
        if self.is_initialised:
            OUT.error('repo %s already initialised', self.path)
            return
        if self.is_existing:
            raise ValueError('directory already exists... please check, delete it, and try again')

        if ask(f'Execute "git init {self.path}"?') != 'y':
            OUT.warning('skipping %s', self.path)
            return

        self.repo = RepoData(git.Repo.init(normalize_path(str(self.path))))

        for remote_name, remote_url in self.remotes.items():
            self.repo.git.remote('add', remote_name, normalize_url(remote_url))

    def fetch(self, all_remotes: bool = False) -> None:
        """Execute "git fetch --prune" on a remote of tracking branch of current branch.

        Or execute "git fetch --prune" for all remotes.
        """
        if not self.is_existing:
            OUT.info('skipping non-existing "%s"...', self.path)
            return
        if self.repo is None:
            self.link_repo()
        assert self.repo is not None
        self.repo.refresh()

        if all_remotes:
            remote_names = self.repo.remotes
        else:
            remote_names = self._determine_remotes_to_fetch()

        self._fetch_remotes(*remote_names)

    def _determine_remotes_to_fetch(self):
        assert self.repo is not None
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

    def _fetch_remote(self, remote_name: str) -> None:
        assert self.repo is not None
        fetch_infos: t.Sequence[git.FetchInfo]
        try:
            progress = ActionProgress()
            fetch_infos = self.repo.remotes[remote_name].fetch(prune=True, progress=progress)
            progress.finalize()
        except git.GitCommandError as err:
            raise ValueError(f'error while fetching remote "{remote_name}"'
                             f' ("{self.repo.remotes[remote_name].url}") in "{self.name}"') from err
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
        # return fetch_infos

    def _fetch_remotes(self, *remote_names: str) -> None:
        for remote_name in remote_names:
            self._fetch_remote(remote_name)

    def _print_fetch_info(self, fetch_info: git.FetchInfo) -> None:
        info_strings, prefix = create_fetch_info_strings(fetch_info)
        if not info_strings:
            return
        level = logging.WARNING if fetch_info.flags & git.FetchInfo.HEAD_UPTODATE \
            else logging.CRITICAL
        OUT.log(level, '%s fetched "%s" in "%s"; %s',
                prefix, fetch_info.ref, self.name, ', '.join(info_strings))

    def checkout(self) -> None:
        """Interactively select revision and execute "git checkout <revision>" on it.

        The list of branches to select from is composed by combining:
        - local branches
        - non-tracking branches on all remotes
        - local tags
        """
        if not self.is_existing:
            OUT.info('skipping non-existing "%s"...', self.path)
            return
        if self.repo is None:
            self.link_repo()
        assert self.repo is not None
        self.repo.refresh()

        # if self.is_on_only_branch():
        #    return

        keys = r'1234567890abcdefghijklmopqrstuvwxz' \
            r'ABCDEFGHIJKLMOPRSTUVWXZ' \
            r''',.!?*&^%$#@;:'"/|\()[]<>{}-_+=~`'''
        revisions = self._prepare_checkout_list(keys)

        print('Checkout options:')
        for key, (revision, comment) in revisions.items():
            if comment is None:
                print(f'  {key}: {revision}')
            else:
                print(f'  {key}: {revision} ({comment})')

        answer = ask('Which branch to checkout?', answers=list(keys[:len(revisions)] + 'n'))
        if answer == 'n':
            return
        target, _ = revisions[answer]
        if target == self.repo.active_branch:
            return

        self.repo.git.checkout(target)

    def _prepare_checkout_list(self, keys: str):
        assert self.repo is not None
        revisions = collections.OrderedDict()

        local_branches = list(self.repo.branches)
        remote_tracking_branches = set(self.repo.tracking_branches.values())
        remote_nontracking_branches = [
            (remote, branch) for remote, branch in self.repo.remote_branches.items()
            if (remote, branch) not in remote_tracking_branches and branch not in _SPECIAL_REFS]
        local_tags = list(self.repo._repo.tags)

        all_candidates_count: int = \
            len(local_branches) + len(remote_nontracking_branches) + len(local_tags)
        if all_candidates_count > len(keys):
            raise RuntimeError(
                'not enough available keys to create a single list of checkout candidates'
                f' - there are {len(keys)} keys ("{keys}") but {all_candidates_count} candidates:'
                f'\n- branches:{local_branches}, {remote_nontracking_branches}'
                f'\n- tags: {local_tags}')

        index = 0
        for branch in self.repo.branches:
            revisions[keys[index]] = (branch, None)
            index += 1

        for tag in self.repo._repo.tags:
            revisions[keys[index]] = (tag, 'tag')
            index += 1

        for (remote, branch) in self.repo.remote_branches.items():
            if (remote, branch) in remote_tracking_branches \
                    or branch in _SPECIAL_REFS:
                continue
            if branch in self.repo.branches:
                to_checkout = f'{remote}/{branch}'
            else:
                to_checkout = branch
            revisions[keys[index]] = (to_checkout, f'based on {remote}')
            index += 1

        if self.repo.active_branch is None:
            revisions['n'] = ('---', 'keep no branch/tag')
        else:
            # assert revisions['1'][0] == active_branch
            for key, (revision, comment) in revisions.items():
                if revision == self.repo.active_branch:
                    _ = 'no change'
                    comment = f'{comment}, {_}' if comment else _
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
        assert self.repo is not None

        branches_to_push = []  # type: t.List[str]

        if all_branches:
            raise NotImplementedError('pushing not yet implemented')

        if self.repo.active_branch is None:
            OUT.warning('not pushing "%s" because there is no active branch...', self.path)
            return

        branches_to_push.append(self.repo.active_branch)

        pushed_branches_per_remote = {}  # type: t.Dict[str, t.Dict[str, t.Optional[str]]]
        for local_branch in branches_to_push:
            tracking_branch = self.repo.tracking_branches[local_branch]
            if tracking_branch is None:
                remote = next(iter(self.repo.remotes.keys()))
                OUT.warning('pushing "%s" to "%s"...', self.path, remote)
                remote_branch = None
            else:
                remote, remote_branch = tracking_branch
            if remote in pushed_branches_per_remote:
                pushed_branches_per_remote[remote][local_branch] = remote_branch
            else:
                pushed_branches_per_remote[remote] = {local_branch: remote_branch}

        for remote_name, branch_mapping in pushed_branches_per_remote.items():
            push_infos = self._push_single_remote(remote_name, branch_mapping)
            for push_info in push_infos:
                self._print_push_info(push_info)

    def _push_single_remote(
            self, remote_name: str,
            branch_mapping: t.Mapping[str, t.Optional[str]]) -> t.Sequence[git.PushInfo]:
        assert self.repo is not None
        push_refspec = [f'{local_branch}' if remote_branch is None
                        else f'{local_branch}:{remote_branch}'
                        for local_branch, remote_branch in branch_mapping.items()]
        _LOG.warning('push refspec: %s', push_refspec)
        try:
            progress = ActionProgress()
            push_infos = self.repo.remotes[remote_name].push(
                refspec=push_refspec, with_extended_output=True, progress=progress)
            progress.finalize()
        except git.GitCommandError as err:
            raise ValueError(
                f'error while pushing branches {branch_mapping} to remote "{remote_name}"'
                f' ("{self.repo.remotes[remote_name].url}") in "{self.name}"') from err
        return push_infos

    def _print_push_info(self, push_info: git.PushInfo) -> None:
        info_strings, prefix = create_push_info_strings(push_info)
        if not info_strings:
            return
        level = logging.WARNING if push_info.flags & git.PushInfo.UP_TO_DATE \
            else logging.CRITICAL
        OUT.log(level, '%s pushed "%s" to "%s" in "%s"; %s', prefix, push_info.local_ref,
                push_info.remote_ref, self.name, ', '.join(info_strings))

    def collect_garbage(self) -> None:
        """Execute "git gc --agressive --prune"."""
        if not self.is_existing:
            OUT.info('skipping non-existing "%s"...', self.path)
            return
        if self.repo is None:
            self.link_repo()
        assert self.repo is not None

        try:
            self.repo.git.gc(aggressive=True, prune=True)
        except git.GitCommandError as err:
            raise ValueError(f'error while collecting garbage in "{self.path}"') from err

    def status(self, ignored: bool = False) -> None:
        """Execute "git status --short" and run "git gui" if there is any output.

        The "ignored" flag is equivalent to adding "--ignored".
        """
        if not self.is_existing:
            OUT.info('skipping non-existing "%s"...', self.path)
            return
        if self.repo is None:
            self.link_repo()
        assert self.repo is not None

        try:
            status_log = self.repo.git.status(short=True, branch=True, ignored=ignored).splitlines()
        except git.GitCommandError as err:
            raise ValueError(f'error while getting status of "{self.path}"') from err

        if len(status_log) > 1:
            OUT.critical('!! unclear status in "%s":', self.path)
            for line in status_log:
                OUT.critical(line)

        self.repo.refresh()
        self._status_branch()
        self._status_remotes()

    def _get_log(self, start_ref: str, end_ref: str) -> str:
        """Get log as if start_ref..end_ref was used."""
        assert self.repo is not None
        refs = f'{start_ref}..{end_ref}'
        try:
            git_log = self.repo.git.log('--color=always', '--pretty=oneline', refs)
        except git.GitCommandError as err:
            raise RuntimeError(f'error while getting log for "{refs}" of "{self.path}"') from err
        return git_log.splitlines()

    def _print_log(self, ref_log, printed_header: str = '', head_count: int = 10,
                   tail_count: int = 10) -> None:
        if printed_header:
            OUT.critical(printed_header)
        if len(ref_log) > head_count + tail_count + 1:
            for line in ref_log[:head_count]:
                OUT.critical(line)
            OUT.critical(
                '... skipped %i commits', len(ref_log) - head_count - tail_count)
            for line in ref_log[-tail_count:]:
                OUT.critical(line)
        else:
            for line in ref_log:
                OUT.critical(line)

    def _status_branch(self, branch: str = None) -> None:
        """Evaluate the status of single branch by comparing it to the remote branch.

        auto-answers used in this function: create_remote_branch, push, merge, forget_locally
        """
        assert self.repo is not None
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
        try:
            self.repo.git.rev_parse(tracking_branch)
        except:
            OUT.warning(
                'cannot diagnose branch status in "%s"'
                ' -- tracking branch of the current branch does not exist', self.path)
            return
        not_pushed_log = self._get_log(tracking_branch, branch)
        if not_pushed_log:
            self._print_log(not_pushed_log, f'!! not pushed commits from "{branch}"'
                            f' to "{tracking_branch}" in "{self.path}":')
            # self.push_single_remote(
            #    tracking_branch_data[0], ['{0}:{0}'.for.mat(branch, tracking_branch_data[1])])
        not_merged_log = self._get_log(branch, tracking_branch)
        if not_merged_log:
            self._print_log(not_merged_log, f'!! not merged commits from "{tracking_branch}"'
                            f' to "{branch}" in "{self.path}":')
            # answer = self.interface.get_answer('merge')
            # if answer in ['y', 'm']:
            #     self.merge_single_branch(remote, branch)
            # elif answer == 'b':
            #     self.rebase_single_branch(remote, branch)
            # elif answer == 'r':
            #     self.hard_reset_single_branch(remote, branch)
            # elif self.interface.confirm('forget_locally'):
            #     self.repo.git.update_ref(f'refs/remotes/{remote}/{branch}', branch)

    def _status_remotes(self):
        assert self.repo is not None
        assert all(len(list(v.urls)) == 1 for v in self.repo.remotes.values()), self.repo.remotes
        remote_names_in_config = set(self.remotes)
        remote_names = set(self.repo.remotes)
        remotes_in_config = {k: v.replace('\\', '/') for k, v in self.remotes.items()}
        remotes = {k: tuple(v.urls)[0].replace('\\', '/') for k, v in self.repo.remotes.items()}

        extra_remote_names = remote_names - remote_names_in_config
        missing_remote_names = remote_names_in_config - remote_names
        extra_remotes = dict(set(remotes.items()) - set(remotes_in_config.items()))
        missing_remotes = dict(set(remotes_in_config.items()) - set(remotes.items()))
        if not extra_remotes and not missing_remotes:
            return
        OUT.critical('!! repo "%s" has different remotes than it should', self.path)

        for name, url in extra_remotes.items():
            if url in missing_remotes.values():
                OUT.critical('!! renamed remote: "%s"', name)
                new_name = [k for k, v in missing_remotes.items() if url == v][0]
                ans = ask(f'Rename remote from "{name}" to "{new_name}"?')
                if ans == 'y':
                    self.repo.git.remote('rename', name, new_name)
                    del missing_remotes[new_name]
            elif name in missing_remotes.keys():
                OUT.critical('!! url changed for remote: "%s"', name)
                ans = ask(f'Change URL of remote "{name}" from "{url}"'
                          f' to "{remotes_in_config[name]}"?')
                if ans == 'y':
                    self.repo.git.remote('set-url', name, remotes_in_config[name])
                    del missing_remotes[name]
            else:
                OUT.critical('!! extra remote: "%s"', name)
                if name not in extra_remote_names:
                    OUT.critical('!! misconfigured remote: "%s"', name)
                    continue
                ans = ask(f'Remove remote "{name}" with url "{remotes[name]}"?')
                if ans == 'y':
                    self.repo.git.remote('remove', name)

        for name, url in missing_remotes.items():
            OUT.critical('!! missing remote: "%s"', name)
            if name not in missing_remote_names:
                OUT.critical('!! misconfigured remote: "%s"', name)
                continue
            ans = ask(f'Add remote "{name}" with url "{self.remotes[name]}"?')
            if ans == 'y':
                self.repo.git.remote('add', name, self.remotes[name])

    def __str__(self):
        fields = [f'path="{self.path}"']
        if not self.is_initialised:
            if not self.is_existing:
                fields.append('not existing')
            else:
                fields.append('not initialized')
        if self.tags:
            fields.append(f'tags={self.tags}')
        return f'{self.name} ({", ".join(fields)})'
