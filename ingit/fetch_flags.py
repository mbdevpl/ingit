# Copyright (C) 2015-2016  Mateusz Bysiek  http://mbdev.pl/
# This file is part of ingit.
#
# ingit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ingit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ingit.  If not, see <http://www.gnu.org/licenses/>.

"""
Defines valid flags for git.FetchInfo.

functions: info_for_known_flags, info_for_unknown_flags, create_fetch_info_strings
"""

import functools
import operator
import typing

import git

# list used by __create_fetch_info_strings()
_KNOWN_STRINGS = {
    git.FetchInfo.NEW_TAG: 'new tag', # 1
    git.FetchInfo.NEW_HEAD: 'new branch', # 2
    git.FetchInfo.HEAD_UPTODATE: 'already up to date', # 4
    git.FetchInfo.TAG_UPDATE: 'tag update', # 8
    git.FetchInfo.REJECTED: 'rejected', # 16
    git.FetchInfo.FORCED_UPDATE: 'orced update', # 32
    git.FetchInfo.FAST_FORWARD: 'can be fast-forwarded', # 64
    git.FetchInfo.ERROR: 'error' # 128
}

_KNOWN_FLAGS = functools.reduce(operator.or_, _KNOWN_STRINGS.keys())

def info_for_known_flags(
        flags: int, known_strings: typing.Mapping[typing.Any, str]) -> typing.MutableSequence[str]:
    """ Creates string sequence that represents given flags according to given mapping. """
    info_strings = []
    for key, value in known_strings.items():
        if flags & key:
            info_strings.append(value)
    return info_strings

def info_for_unknown_flags(flags: int, known_flags: int) -> typing.MutableSequence[str]:
    """
    Creates string sequence that represents unknown flags according to given known flags mask.
    """
    info_strings = []
    unknown_flags = flags & ~(known_flags)
    if unknown_flags:
        info_strings.append(
            'unknown flag(s): {0} ({0:032b})'.format(unknown_flags))
    return info_strings

def create_fetch_info_strings(i: git.FetchInfo):
    """ Creates FetchInfo strings. """
    info_strings = info_for_known_flags(i.flags, _KNOWN_STRINGS)
    prefix = '!!'
    if i.flags & i.HEAD_UPTODATE:
        prefix = '--'
    info_strings += info_for_unknown_flags(i.flags, _KNOWN_FLAGS)
    if i.note:
        info_strings.append('note: {0}'.format(i.note.strip()))
    return (info_strings, prefix)
