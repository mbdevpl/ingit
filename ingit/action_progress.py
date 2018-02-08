"""Monitoring progress of git operations."""

import functools
import operator
import os
import shutil
import sys

import git
import git.remote

# list used by __create_operation_strings()
_KNOWN_OPERATIONS_STRINGS = {
    git.remote.RemoteProgress.BEGIN: 'begun',  # 1
    git.remote.RemoteProgress.END: 'ended',  # 2
    git.remote.RemoteProgress.COUNTING: 'counting objects',  # 4
    git.remote.RemoteProgress.COMPRESSING: 'compressing',  # 8
    git.remote.RemoteProgress.WRITING: 'writing',  # 16
    git.remote.RemoteProgress.RECEIVING: 'receiving objects',  # 32
    git.remote.RemoteProgress.RESOLVING: 'resolving deltas',  # 64
    git.remote.RemoteProgress.FINDING_SOURCES: 'finding sources',  # 128
    256: 'cloning url',
    512: 'fetching remote of submodule',
    # git.remote.RemoteProgress.CHECKING_OUT
}
_KNOWN_OPERATIONS = functools.reduce(operator.or_, _KNOWN_OPERATIONS_STRINGS.keys())
_KNOWN_OPERATIONS_PHASES = git.remote.RemoteProgress.BEGIN | git.remote.RemoteProgress.END

_CARET_UP = '\033[1A'  # TODO: works only in bash, but what about cmd?


def _create_operation_strings(op_code):
    """ Creates operation strings. """
    operation_strings = []
    for key, value in _KNOWN_OPERATIONS_STRINGS.items():
        if op_code & key:
            operation_strings.append(value)
    unknown_operations = op_code & ~(_KNOWN_OPERATIONS)
    if unknown_operations:
        operation_strings.append(
            'unknown operation code(s): {0} ({0:032b})'.format(unknown_operations))
    return operation_strings


class ActionProgress(git.remote.RemoteProgress):

    """Emulate usual git progress reports in the console when working with GitPython."""

    def __init__(self, inline: bool = True, f_d=None):
        """When no redirected_output_fd is given, use stdout."""
        assert isinstance(inline, bool)

        super().__init__()
        self.printed_lines = False
        self.line_len = 0  # type: int
        try:
            self.term_size = shutil.get_terminal_size()  # type: int
        except ValueError:
            self.term_size = os.terminal_size((80, 24))
        assert self.term_size.columns > 0

        self.inline = inline
        self.f_d = f_d if f_d else sys.stdout

    def _print_without_nl(self, text: str):
        if self.inline:
            print(text, end='', flush=True, file=self.f_d)
        else:
            self._print_with_nl(text)

    def _print_with_nl(self, text: str):
        print(text, file=self.f_d)

    def update(self, op_code: int, cur_count, max_count=None, message: str = ''):
        """Override git.remote.RemoteProgress.update()."""
        operation_strings = _create_operation_strings(op_code)
        description = '{}: '.format(' '.join(operation_strings)) if operation_strings else ''
        progress = ''
        if cur_count:
            progress += str(int(cur_count))
        if cur_count and max_count:
            progress += '/'
        if max_count:
            progress += str(int(max_count))
        if cur_count and max_count:
            max_c = max_count or 100
            progress = '{:3.0%} ({})'.format(cur_count / max_c, progress)
        if message:
            if message.startswith(', '):
                message = message[2:]
            message = ' - ' + message
        else:
            message = ''
        if self.inline and self.line_len > 0:
            if self.line_len < self.term_size.columns:
                self._print_without_nl('\r{}\r'.format(' ' * self.line_len))
            else:
                self._print_without_nl('\r{}\r'.format(' ' * (self.term_size.columns - 1)))
                self._print_without_nl(_CARET_UP)
                self._print_without_nl('{}\r'.format(' ' * (self.term_size.columns - 1)))
        line = '{0}{1}{2}'.format(description, progress, message)
        self.line_len = len(line)
        self._print_without_nl(line)
        self.printed_lines = True

    def finalize(self):
        """This should be ran after the last progress report."""
        if self.printed_lines:
            if self.inline:
                self._print_with_nl('')
            self.printed_lines = False
            self.line_len = 0
