.. role:: bash(code)
    :language: bash

.. role:: json(code)
    :language: json


=====
ingit
=====

.. image:: https://img.shields.io/pypi/v/ingit.svg
    :target: https://pypi.org/project/ingit
    :alt: package version from PyPI

.. image:: https://travis-ci.org/mbdevpl/ingit.svg?branch=master
    :target: https://travis-ci.org/mbdevpl/ingit
    :alt: build status from Travis CI

.. image:: https://ci.appveyor.com/api/projects/status/github/mbdevpl/ingit?branch=master&svg=true
    :target: https://ci.appveyor.com/project/mbdevpl/ingit
    :alt: build status from AppVeyor

.. image:: https://codecov.io/gh/mbdevpl/ingit/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/mbdevpl/ingit
    :alt: test coverage from Codecov

.. image:: https://img.shields.io/github/license/mbdevpl/ingit.svg
    :target: https://github.com/mbdevpl/ingit/blob/master/NOTICE
    :alt: license

Tool for managing a large collection of repositories in git. If you have 100 git-versioned projects,
keeping tabs on everything can be quite troublesome.

That's where *ingit* comes in. It mimics selected git commands, however you can perform the same
action on a group of repositories instead of just one.

Additionally, it has an interactive mode in which you can go over your repositories and quickly
perform typical suggested actions in each individual repository based on its current status.

.. contents::
    :backlinks: none


Overview
========


Basic usage
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

*   ``ingit summary`` will show summary of repositories registered in ingit;
*   ``ingit register`` will add an existing git repository to ingit configuration.


Currently available git-like commands are:

*   ``ingit clone`` will mass-clone registered repositories;
*   ``ingit init`` will mass-init registered repositories;
*   ``ingit fetch`` will mass-fetch existing registered repositories;
*   ``ingit checkout`` will interactively checkout branches;
*   ``ingit merge`` will interactively merge branches;
*   ``ingit push`` will mass-push existing registered repositories;
*   ``ingit gc`` will do mass garbage collection of existing registered repositories;
*   ``ingit status`` will give comprehensive status report for every existing registered repository.



Configuration
-------------

Ingit works based on configuration in 2 JSON files:

*   runtime configuration
*   repositories configuraion

If either of the files doesn't exist, detaults will be generated.

The default paths to the files can be overriden via ``--config`` and ``--repos``
command-line options.


runtime configuraion
~~~~~~~~~~~~~~~~~~~~

Most importantly, stores repositories root directory -- it's a directory which ingit assumes
to contain git-versioned projects.

Example:

.. code:: json

    {
      "description": "ingit runtime configuration file",
      "ingit-version": "0.4.0",
      "machines": [
        {
          "name": "desktop",
          "repos_path": "~/Projects"
        },
        {
          "interactive": false,
          "names": ["server", "server.domain.com"],
          "repos_path": "$HOME/Projects"
        }
      ]
    }


repositories configuraion
~~~~~~~~~~~~~~~~~~~~~~~~~

It's a file that lists all registered projects and keeps their metadata.

Example:

.. code:: json

    {
      "description": "ingit repositories configuration file",
      "ingit-version": "0.4.0",
      "repos": [
        {
          "name": "ingit",
          "remotes": {
            "github": "git@github.com:mbdevpl/ingit.git"
          },
          "tags": [
            "active",
            "git",
            "github",
            "my",
            "python"
          ]
        },
        {
          "name": "pylint",
          "remotes": {
            "github": "git@github.com:mbdevpl/pylint.git",
            "source": "https://github.com/PyCQA/pylint"
          },
          "tags": [
            "external",
            "github",
            "python"
          ]
        }
      ]
    }


Command details
===============

Below, details of each command are described.


``ingit summary``
-----------------

Show summary of registered repositories and status of configured repository root.

First of all, print a list of registered repositories. By default, all registered repositories
are listed, but, as in case of most commands, the results can be filtered via a predicate or regex.

Independently, print a list of all unregistered repositories and all not versioned paths present
in the configured repositories root.


``ingit register``
------------------

Start tracking a repository in ingit.

.. code:: bash

    ingit register [--tags TAG ...] [PATH]

The initial configuration is set according to basic repository information:
its root directory name becomes "name", its absolute path becomes "path", and
its currently configured remotes become "remotes". You can edit the
configuration manually afterwards.

Use ``PATH`` to provide the path to root directory of repository.
If not provided, current working directory is used.

Use ``--tags`` to provide tags for this repository, they will be added to the initial configuration.


``ingit status``
----------------

Perform git status, as well as other diagnostic git commands.

Execute:

*   ``git status --short`` to inform about any uncommited changes,
*   ``git log tracking_branch..branch`` to inform about commits that are not yet pushed to the remote,
*   ``git log branch..tracking_branch`` to inform about commits that are not yet merged from the remote.

Additionally, compare registered remotes with actual remotes to make sure that ingit
configuration is in sync with the repository metadata.


Other commands
--------------

TODO: Write docs for other commands.


Requirements
============

Python version 3.5 or later.

Python libraries as specified in `<requirements.txt>`_.

Building and running tests additionally requires packages listed in `<test_requirements.txt>`_.

Tested on Linux, OS X and Windows.
