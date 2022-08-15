"""Initialization of tests of ingit package."""

import logging
import os

from ingit import _logging


class Logging(_logging.Logging):
    """Test logging configuration."""

    level_package = logging.DEBUG


Logging.configure_basic()

if 'EXAMPLE_PROJECTS_PATH' not in os.environ:
    os.environ['EXAMPLE_PROJECTS_PATH'] = '..'
