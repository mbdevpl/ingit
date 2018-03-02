"""Unit tests for ingit runtime."""

import logging
import pathlib
import platform
import tempfile
import unittest
import unittest.mock

import readchar

from ingit.runtime import Runtime

_LOG = logging.getLogger(__name__)


class Tests(unittest.TestCase):

    def setUp(self):
        with tempfile.NamedTemporaryFile() as tmp_file1:
            with tempfile.NamedTemporaryFile() as tmp_file2:
                self.repos_config_path = pathlib.Path(tmp_file2.name)
            self.runtime_config_path = pathlib.Path(tmp_file1.name)

    def test_register_machine(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            runtime = Runtime(self.runtime_config_path, self.repos_config_path)
        runtime.register_machine('blah')

    def test_register_machine_existing(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            runtime = Runtime(self.runtime_config_path, self.repos_config_path)
        with self.assertRaises(ValueError):
            runtime.register_machine(platform.node())
