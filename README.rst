.. role:: bash(code)
    :language: bash


=====
ingit
=====

.. image:: https://img.shields.io/pypi/v/ingit.svg
    :target: https://pypi.python.org/pypi/ingit
    :alt: package version from PyPI

.. image:: https://travis-ci.org/mbdevpl/ingit.svg?branch=master
    :target: https://travis-ci.org/mbdevpl/ingit
    :alt: build status from Travis CI

.. image:: https://ci.appveyor.com/api/projects/status/github/mbdevpl/ingit?svg=true
    :target: https://ci.appveyor.com/project/mbdevpl/ingit
    :alt: build status from AppVeyor

.. image:: https://codecov.io/gh/mbdevpl/ingit/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/mbdevpl/ingit
    :alt: test coverage from Codecov

.. image:: https://img.shields.io/pypi/l/ingit.svg
    :target: https://github.com/mbdevpl/ingit/blob/master/NOTICE
    :alt: license

Tool for managing a large collection of repositories in git. If you have 100 git-versioned projects,
keeping tabs on everything can be quite troublesome.

That's where *ingit* comes in. It mimics selected git commands, however you can perform the same
action on a group of repositories instead of just one.

Additionally, it has an interactive mode in which you can go over your repositories and quickly
perform typical suggested actions in each individual repository based on its current status.


overview
========


basic usage
-----------

For general help, see:

.. code:: bash

    ingit -h


For command-specific help, see:

.. code:: bash

    ingit command -h


Commands are of two kinds in general:

*   git-like commands, which work similar to their git versions;
*   ingit-only commands, which you won't find in git.


Currently available ingit-only commands are:

.. code:: bash

    ingit summary
    ingit register


Currently available git commands are:

.. code:: bash

    ingit clone
    ingit init
    ingit fetch
    ingit checkout
    ingit merge
    ingit push
    ingit gc
    ingit status


requirements
============

Python version >= 3.5.

Python libraries as specified in `<requirements.txt>`_.

Building and running tests additionally requires packages listed in `<test_requirements.txt>`_.

Tested on Linux, OS X and Windows.
