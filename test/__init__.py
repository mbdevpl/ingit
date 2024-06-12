"""Initialization of tests for ingit package."""

import logging

from ingit.__main__ import Logging


class TestsLogging(Logging):
    """Test logging configuration."""

    level_global = logging.DEBUG


TestsLogging.configure()
