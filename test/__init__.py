"""Initialization of tests of ingit package."""

import logging
import os

from ingit.__main__ import Logging


class TestsLogging(Logging):
    """Test logging configuration."""

    level_package = logging.DEBUG


TestsLogging.configure_basic()
