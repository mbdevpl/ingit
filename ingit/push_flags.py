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
Defines valid flags for git.PushInfo.

function: create_push_info_strings
"""

import functools
import operator

import git

from .fetch_flags import info_for_known_flags, info_for_unknown_flags

# used by __create_push_info_strings()
_KNOWN_STRINGS = {
    git.PushInfo.NEW_TAG: 'new tag', # 1
    git.PushInfo.NEW_HEAD: 'new branch', # 2
    git.PushInfo.NO_MATCH: 'no match', # 4
    git.PushInfo.REJECTED: 'rejected', # 8
    git.PushInfo.REMOTE_REJECTED: 'remote rejected', # 16
    git.PushInfo.REMOTE_FAILURE: 'remote failure', # 32
    git.PushInfo.DELETED: 'deleted', # 64
    git.PushInfo.FORCED_UPDATE: 'forced update', # 128
    git.PushInfo.FAST_FORWARD: 'was fast-forwarded', # 256
    git.PushInfo.UP_TO_DATE: 'already up to date', # 512
    git.PushInfo.ERROR: 'error' # 1024
}

_KNOWN_FLAGS = functools.reduce(operator.or_, _KNOWN_STRINGS.keys())

def create_push_info_strings(i: git.PushInfo):
    """ Creates PushInfo strings. """

    info_strings = info_for_known_flags(i.flags, _KNOWN_STRINGS)
    prefix = '!!'
    if i.flags & i.UP_TO_DATE:
        prefix = '--'
    info_strings += info_for_unknown_flags(i.flags, _KNOWN_FLAGS)
    if i.summary:
        info_strings.append('summary: {0}'.format(i.summary.strip()))
    return (info_strings, prefix)
