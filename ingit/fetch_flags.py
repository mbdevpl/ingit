"""Human-readable information extraction from git.FetchInfo."""

import functools
import operator
import typing as t

import git

# list used by __create_fetch_info_strings()
_KNOWN_STRINGS = {
    git.FetchInfo.NEW_TAG: 'new tag',  # 1
    git.FetchInfo.NEW_HEAD: 'new branch',  # 2
    git.FetchInfo.HEAD_UPTODATE: 'already up to date',  # 4
    git.FetchInfo.TAG_UPDATE: 'tag update',  # 8
    git.FetchInfo.REJECTED: 'rejected',  # 16
    git.FetchInfo.FORCED_UPDATE: 'forced update',  # 32
    git.FetchInfo.FAST_FORWARD: 'can be fast-forwarded',  # 64
    git.FetchInfo.ERROR: 'error'  # 128
}

_KNOWN_FLAGS = functools.reduce(operator.or_, _KNOWN_STRINGS.keys())


def info_for_known_flags(
        flags: int, known_strings: t.Mapping[t.Any, str]) -> t.MutableSequence[str]:
    """Create string sequence that represents given flags according to given mapping."""
    info_strings = []
    for key, value in known_strings.items():
        if flags & key:
            info_strings.append(value)
    return info_strings


def info_for_unknown_flags(flags: int, known_flags: int) -> t.MutableSequence[str]:
    """Create string sequence that represents unknown flags according to given known flags mask.s"""
    info_strings = []
    unknown_flags = flags & ~(known_flags)
    if unknown_flags:
        info_strings.append(
            'unknown flag(s): {0} ({0:032b})'.format(unknown_flags))
    return info_strings


def create_fetch_info_strings(info: git.FetchInfo):
    """Create FetchInfo strings."""
    info_strings = info_for_known_flags(info.flags, _KNOWN_STRINGS)
    prefix = '!!'
    if info.flags & info.HEAD_UPTODATE:
        prefix = '--'
    info_strings += info_for_unknown_flags(info.flags, _KNOWN_FLAGS)
    if info.note:
        info_strings.append('note: {0}'.format(info.note.strip()))
    return (info_strings, prefix)
