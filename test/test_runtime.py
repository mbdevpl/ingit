"""Unit tests for ingit runtime."""

import logging
import pathlib
import platform
import shutil
import tempfile
import unittest
import unittest.mock

import readchar

from ingit.runtime import Runtime

HERE = pathlib.Path(__file__).resolve().parent

_LOG = logging.getLogger(__name__)


class Tests(unittest.TestCase):

    def setUp(self):
        with tempfile.NamedTemporaryFile() as tmp_file1:
            with tempfile.NamedTemporaryFile() as tmp_file2:
                self.repos_config_path = pathlib.Path(tmp_file2.name)
            self.runtime_config_path = pathlib.Path(tmp_file1.name)

    def tearDown(self):
        if self.runtime_config_path.is_file():
            self.runtime_config_path.unlink()
        if self.repos_config_path.is_file():
            self.repos_config_path.unlink()

    def test_nothing(self):
        pass

    def test_create_configs(self):
        self.assertFalse(self.runtime_config_path.is_file())
        self.assertFalse(self.repos_config_path.is_file())
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            runtime = Runtime(self.runtime_config_path, self.repos_config_path)
        self.assertEqual(self.runtime_config_path, runtime.runtime_config_path)
        self.assertEqual(self.repos_config_path, runtime.repos_config_path)
        self.assertTrue(self.runtime_config_path.is_file())
        self.assertTrue(self.repos_config_path.is_file())

    def test_register_machine(self):
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            runtime = Runtime(self.runtime_config_path, self.repos_config_path)
        runtime.register_machine('blah')
        self.assertIn('blah', [machine['name'] for machine in runtime.runtime_config['machines']])
        with self.assertRaises(ValueError):
            runtime.register_machine(platform.node())

    def test_autoadd_machine(self):
        """Test adding machine into an existing config."""
        runtime_config_path = pathlib.Path(HERE, 'examples', 'runtime_config', 'example_names.json')
        shutil.copy(str(runtime_config_path), str(self.runtime_config_path))
        with unittest.mock.patch.object(readchar, 'readchar', return_value='n'):
            with self.assertRaises(ValueError):
                Runtime(self.runtime_config_path, self.repos_config_path)
        with unittest.mock.patch.object(readchar, 'readchar', return_value='y'):
            runtime = Runtime(self.runtime_config_path, self.repos_config_path)
        self.assertIn(platform.node(), [
            machine.get('name') for machine in runtime.runtime_config['machines']])
