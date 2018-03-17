"""Human-readable information extraction from git.PushInfo."""

import functools
import operator

import git

from .fetch_flags import info_for_known_flags, info_for_unknown_flags

# used by __create_push_info_strings()
_KNOWN_STRINGS = {
    git.PushInfo.NEW_TAG: 'new tag',  # 1
    git.PushInfo.NEW_HEAD: 'new branch',  # 2
    git.PushInfo.NO_MATCH: 'no match',  # 4
    git.PushInfo.REJECTED: 'rejected',  # 8
    git.PushInfo.REMOTE_REJECTED: 'remote rejected',  # 16
    git.PushInfo.REMOTE_FAILURE: 'remote failure',  # 32
    git.PushInfo.DELETED: 'deleted',  # 64
    git.PushInfo.FORCED_UPDATE: 'forced update',  # 128
    git.PushInfo.FAST_FORWARD: 'was fast-forwarded',  # 256
    git.PushInfo.UP_TO_DATE: 'already up to date',  # 512
    git.PushInfo.ERROR: 'error'  # 1024
}

_KNOWN_FLAGS = functools.reduce(operator.or_, _KNOWN_STRINGS.keys())


def create_push_info_strings(info: git.PushInfo):
    """Create PushInfo strings."""
    info_strings = info_for_known_flags(info.flags, _KNOWN_STRINGS)
    prefix = '!!'
    if info.flags & info.UP_TO_DATE:
        prefix = '--'
    info_strings += info_for_unknown_flags(info.flags, _KNOWN_FLAGS)
    if info.summary:
        info_strings.append('summary: {0}'.format(info.summary.strip()))
    return (info_strings, prefix)
