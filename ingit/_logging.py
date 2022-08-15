"""Logging configuration."""

import logging

from . import logging_boilerplate


class Logging(logging_boilerplate.Logging):
    """Logging configuration."""

    packages = ['ingit']
    level_package = logging.INFO
