"""Initialization of tests of ingit package."""

import logging
import pathlib

logging.basicConfig()

assert pathlib.Path('..', 'argunparse').is_dir()
assert pathlib.Path('..', 'transpyle').is_dir()
assert pathlib.Path('..', 'typed-astunparse').is_dir()
