"""Unit tests for ingit runtime interface."""

import logging
import unittest
import unittest.mock

import readchar

from ingit.runtime_interface import ask

_LOG = logging.getLogger(__name__)


class Tests(unittest.TestCase):

    def test_ask(self):
        for answer in ('n', 'y'):
            with unittest.mock.patch.object(readchar, 'readchar', return_value=answer):
                actual_answer = ask('Really?')
                self.assertEqual(actual_answer, answer)

    def test_ask_default_answer(self):
        for keypress in ('\n', '\r'):
            with unittest.mock.patch.object(readchar, 'readchar', return_value=keypress):
                actual_answer = ask('Really?')
                self.assertEqual(actual_answer, 'n')
            for deafult_answer in ('n', 'y'):
                with unittest.mock.patch.object(readchar, 'readchar', return_value=keypress):
                    actual_answer = ask('Really?', default=deafult_answer)
                    self.assertEqual(actual_answer, deafult_answer)

    def test_ask_keyboard_interrupt(self):
        with self.assertRaises(KeyboardInterrupt):
            with unittest.mock.patch.object(readchar, 'readchar', return_value=chr(3)):  # Ctrl+C
                ask('Really?')
