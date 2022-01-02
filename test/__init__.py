"""Initialization of tests of ingit package."""

import logging
import os

logging.basicConfig()

if 'EXAMPLE_PROJECTS_PATH' not in os.environ:
    os.environ['EXAMPLE_PROJECTS_PATH'] = '..'
