"""Entry point of the command-line interface of ingit package."""

# PYTHON_ARGCOMPLETE_OK

import logging

import boilerplates.logging

from .main import main


class Logging(boilerplates.logging.Logging):
    """Logging configuration."""

    packages = ['ingit']
    level_global = logging.INFO


if __name__ == '__main__':
    Logging.configure()
    main()
