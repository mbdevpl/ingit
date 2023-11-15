"""Monitoring progress of git operations."""

import functools
import operator
import logging
import shutil
import sys
import typing as t

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
_KNOWN_OPERATIONS: int = functools.reduce(operator.or_, _KNOWN_OPERATIONS_STRINGS.keys())
_KNOWN_OPERATIONS_PHASES = git.remote.RemoteProgress.BEGIN | git.remote.RemoteProgress.END

_CARET_UP = '\033[1A'  # TODO: works only in bash, but what about cmd?

_LOG = logging.getLogger(__name__)


def _create_operation_strings(op_code: int):
    """Create operation strings."""
    operation_strings = []
    for key, value in _KNOWN_OPERATIONS_STRINGS.items():
        if op_code & key:
            operation_strings.append(value)
    unknown_operations = (
        op_code & ~_KNOWN_OPERATIONS)  # pylint: disable = invalid-unary-operand-type
    if unknown_operations:
        operation_strings.append(
            f'unknown operation code(s): {unknown_operations} ({unknown_operations:032b})')
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
            term_size = shutil.get_terminal_size()
        except ValueError:
            self.line_width = 100
        else:
            _LOG.log(logging.WARNING if term_size.columns < 16 else logging.NOTSET,
                     'detected terminal width is %i', term_size.columns)
            self.line_width = term_size.columns if term_size.columns else 100

        assert self.line_width > 0

        self.inline = inline
        self.f_d = f_d if f_d else sys.stdout

    def _print_without_nl(self, text: str):
        if self.inline:
            print(text, end='', flush=True, file=self.f_d)
        else:
            self._print_with_nl(text)

    def _print_with_nl(self, text: str):
        print(text, file=self.f_d)

    def update(self, op_code: int, cur_count: t.Any, max_count: t.Any = None, message: str = ''):
        """Override git.remote.RemoteProgress.update."""
        operation_strings = _create_operation_strings(op_code)
        description = f'{" ".join(operation_strings)}: ' if operation_strings else ''
        progress = ''
        if cur_count:
            progress += str(int(cur_count))
        if cur_count and max_count:
            progress += '/'
        if max_count:
            progress += str(int(max_count))
        if cur_count and max_count:
            max_c = max_count or 100
            progress = f'{cur_count / max_c:3.0%} ({progress})'
        if message:
            if message.startswith(', '):
                message = message[2:]
            message = ' - ' + message
        else:
            message = ''
        if self.inline and self.line_len > 0:
            if self.line_len < self.line_width:
                self._print_without_nl(f'\r{" " * self.line_len}\r')
            else:
                self._print_without_nl(f'\r{" " * (self.line_width - 1)}\r')
                self._print_without_nl(_CARET_UP)
                self._print_without_nl(f'{" " * (self.line_width - 1)}\r')
        line = f'{description}{progress}{message}'
        self.line_len = len(line)
        self._print_without_nl(line)
        self.printed_lines = True

    def finalize(self):
        """To be ran after the last progress report."""
        if self.printed_lines:
            if self.inline:
                self._print_with_nl('')
            self.printed_lines = False
            self.line_len = 0
