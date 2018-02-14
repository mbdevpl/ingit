"""Tests for git operation progress reporting."""

import collections
import logging
import sys
import unittest

from ingit.action_progress import ActionProgress, _KNOWN_OPERATIONS_STRINGS as op_codes


class StreamToLog:

    """Clumsy converter that allows logging instances to be used as a file-like object.

    Given a logging_function, will convert write(text) calls to logging_function(text) calls.
    For example: StreamToLog(logging.warning) will redirect all writes to logging.warning().
    """

    def __init__(self, logging_function: collections.Callable):
        """Construct StreamToLog."""
        assert callable(logging_function)

        self.logging_function = logging_function

    def write(self, message):
        """Redirect the write to the logging function."""
        while message.endswith('\r') or message.endswith('\n'):
            message = message[:-1]
        self.logging_function(message)

    def flush(self):
        """Flush can be a no-op."""
        pass


class ActionProgressTests(unittest.TestCase):

    """Unit tests for ActionProgress."""

    def test_construct(self):
        """Can ActionProgress be constructed?"""
        apr = ActionProgress()
        self.assertIsNotNone(apr)

    def test_update(self):
        """Can ActionProgress be updated?"""
        apr = ActionProgress()
        self.assertIsNotNone(apr)
        self.assertFalse(apr.printed_lines)
        print()
        for op_code in op_codes:
            apr.update(op_code, 0, None)
            self.assertTrue(apr.printed_lines)
        print()

    def test_update_with_percentage(self):
        """Can ActionProgress be updated with percentage info?"""
        apr = ActionProgress()
        self.assertIsNotNone(apr)
        self.assertFalse(apr.printed_lines)
        op_count = len(op_codes)
        op_index = 0
        print()
        for op_code in op_codes:
            op_index += 1
            apr.update(op_code, op_index, op_count)
            self.assertTrue(apr.printed_lines)
        apr.finalize()

    def test_finalize(self):
        """Can ActionProgress be finalised?"""
        apr = ActionProgress()
        self.assertIsNotNone(apr)
        self.assertFalse(apr.printed_lines)
        apr.finalize()
        self.assertFalse(apr.printed_lines)

    def test_update_and_finalize(self):
        """Can ActionProgress be finalised after updating several times?"""
        apr = ActionProgress()
        self.assertIsNotNone(apr)
        self.assertFalse(apr.printed_lines)
        print()
        for op_code in op_codes:
            apr.update(op_code, 0, None)
            self.assertTrue(apr.printed_lines)
        apr.finalize()
        self.assertFalse(apr.printed_lines)

    def test_reuse(self):
        """Can ActionProgress instance be reused?"""
        apr = ActionProgress()
        self.assertIsNotNone(apr)
        self.assertFalse(apr.printed_lines)

        print()
        for op_code in op_codes:
            apr.update(op_code, 0, None)
            self.assertTrue(apr.printed_lines)
        apr.finalize()
        self.assertFalse(apr.printed_lines)

        for op_code in op_codes:
            apr.update(op_code, 0, None)
            self.assertTrue(apr.printed_lines)
        apr.finalize()
        self.assertFalse(apr.printed_lines)

    def test_reuse_after_one_step(self):
        """Can ActionProgress be reused after finalising after only one update?"""
        apr = ActionProgress()
        self.assertIsNotNone(apr)
        self.assertFalse(apr.printed_lines)
        print()
        for op_code in op_codes:
            apr.update(op_code, 0, None)
            self.assertTrue(apr.printed_lines)
            apr.finalize()
            self.assertFalse(apr.printed_lines)

    def test_not_inline(self):
        """Can ActionProgress be ?"""
        apr = ActionProgress(inline=False)
        self.assertIsNotNone(apr)
        print()
        for op_code in op_codes:
            apr.update(op_code, 0, None)
            self.assertTrue(apr.printed_lines)
        apr.finalize()
        self.assertFalse(apr.printed_lines)

    def test_redirect_output(self):
        """Can ActionProgress output be redirected?"""
        apr = ActionProgress(f_d=sys.stderr)
        self.assertIsNotNone(apr)
        print()
        for op_code in op_codes:
            apr.update(op_code, 0, None)
            self.assertTrue(apr.printed_lines)
        apr.finalize()
        self.assertFalse(apr.printed_lines)

    def test_redirect_output_not_inline(self):
        """Can ActionProgress be used in non-inline mode? """
        log_stream = StreamToLog(logging.debug)
        apr = ActionProgress(inline=False, f_d=log_stream)
        self.assertIsNotNone(apr)
        for op_code in op_codes:
            apr.update(op_code, 0, None)
            self.assertTrue(apr.printed_lines)
        log_stream.flush()
        apr.finalize()
        self.assertFalse(apr.printed_lines)

    def test_message(self):
        """Can ActionProgress be updated with custom message?"""
        apr = ActionProgress()
        self.assertIsNotNone(apr)
        self.assertFalse(apr.printed_lines)
        print()
        for op_code in op_codes:
            apr.update(op_code, 0, None, 'testu')
            self.assertTrue(apr.printed_lines)
        apr.finalize()
        self.assertFalse(apr.printed_lines)

    def test_message_unusual(self):
        """Can ActionProgress be updated with message that begins with comma and space?"""
        apr = ActionProgress()
        self.assertIsNotNone(apr)
        self.assertFalse(apr.printed_lines)
        apr.update(next(iter(op_codes)), 0, None, ', testu')
        self.assertTrue(apr.printed_lines)
        apr.finalize()
        self.assertFalse(apr.printed_lines)

    def test_very_long_message(self):
        """Can ActionProgress be updated with message that overflows to next terminal line?"""
        apr = ActionProgress()
        self.assertIsNotNone(apr)
        self.assertFalse(apr.printed_lines)
        print()
        for op_code in op_codes:
            apr.update(op_code, 0, None, 'testu' + ' testu' * 20)
            self.assertTrue(apr.printed_lines)
        apr.finalize()
        self.assertFalse(apr.printed_lines)

    def test_unknown_operation(self):
        """Can ActionProgress be updated with unknown operation code?"""
        apr = ActionProgress()
        self.assertIsNotNone(apr)
        self.assertFalse(apr.printed_lines)
        apr.update(2 ** 11, 0, None, ', this is status message of unknown operation')
        self.assertTrue(apr.printed_lines)
        apr.finalize()
        self.assertFalse(apr.printed_lines)
