.. role:: bash(code)
    :language: bash

.. role:: json(code)
    :language: json

.. role:: python(code)
    :language: python


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


Filtering the repositories
--------------------------

Git-like commands of ingit
(namely: ``ingit clone``, ``ingit init``, ``ingit fetch``, ``ingit checkout``,
``ingit merge``, ``ingit push``, ``ingit gc`` and ``ingit status``),
as well as ``ingit summary``,
by default operate on all registered repositories.

However, they all can take the options ``--regex``/``-r`` and ``--predicate``/``-p``
that filter out the repositories using repository metadata (i.e. name, tags, path and remotes)
which is stored in the repositories configuration.

The ``--regex``/``-r`` option accepts any regular expression (also a simple string)
and filters the repos by trying to simply find a match in any of the metadata.

.. code:: python

    def regex_predicate(regex, name, tags, path, remotes):
        return (
            re.search(regex, name) is not None
            or any(re.search(regex, tag) is not None for tag in tags)
            or re.search(regex, str(path)) is not None
            or any(re.search(regex, name) for name, url in remotes.items()))

The actual implementation is here: `<ingit/runtime.py#L23>`_

The ``--predicate``/``-p`` option accepts a python expression which will be inserted
into a predicate function template, as below:

.. code:: python

    lambda name, tags, path, remotes: (predicate)

The actual implementation is here: `<ingit/main.py#L188>`_

Therefore, executing ``ingit --predicate "'mytag' in tags" fetch`` results
in the following predicate being applied:

.. code:: python

    lambda name, tags, path, remotes: ('mytag' in tags)

And thus only repositories that have ``'mytag'`` in their tags are fetched.

If both ``--regex``/``-r`` and ``--predicate``/``-p`` are provided,
predicate is applied first.


Configuration
-------------

Ingit works based on configuration in 2 JSON files:

*   runtime configuration
*   repositories configuraion

If either of the files doesn't exist, detaults will be generated.

The default paths to the files can be overriden via ``--config`` and ``--repos``
command-line options.


Runtime configuraion
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


Repositories configuraion
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

Normally, resolved absolute path is stored in the configuration.
However, if path is within the configured repos root directory (i.e. "repos_path" in runtime configuraion)
then path relative to the repos root is stored instead.
Additinally, if the repository is stored directly in the configured repos root
(i.e. there are no intermediate directories) then path is not stored at all.

Such behaviour is implemented to make configuration file much less verbose in typical usage scenarios.

To prevent this behaviour, and force all repository paths to be absolute,
simply configure your repos root in runtime configuraion to JSON null,
or something which is expected to never contain any repositories -- like "/dev/null".

Use ``--tags`` to provide tags for this repository, they will be added to the initial configuration.

Tags have no other effect than making repository filtering easier.


``ingit clone``
----------------

Execute ``git clone <remote-url> --recursive --orign <remote-name> <path>``,
where values of ``<path>`` and ``<remote-...>`` are taken from default remote configuration
of the repository.

After cloning, add all remaining configured remotes to the repository and fetch them.

For example, if repository configuration is as follows:

.. code:: json

  {
    "name": "Spack",
    "path": "~/Software/Spack",
    "remotes": {
      "source": "https://github.com/spack/spack.git",
      "github": "git@github.com:mbdevpl/spack.git"
    },
    "tags": []
  }

The clone command will be:
``git clone https://github.com/spack/spack.git --recursive --orign source ~/Software/Spack``
because ``source`` is the first configured remote.
The subsequent commands will be ``git remote add github git@github.com:mbdevpl/spack.git``
and ``git fetch github``.


``ingit init``
----------------

Execute ``git init`` followed by ``git remote add`` for each configured remote.


``ingit fetch``
----------------

Execute ``git fetch <remote-name>``, where the remote name is the remote of the current
tracking branch, or all remotes of the repository if there's no tracking branch,
or repository is in detached head state.

Use ``--all`` to fetch all remotes in all cases.


``ingit checkout``
----------------

Interactively select revision to checkout from list of local branches,
remote non-tracking branches and local tags.

The list of branches to select from is composed by combinig:

- local branches
- non-tracking branches on all remotes
- local tags

Checking out a remote branch will create a local branch with the same unless it already exists.
If it already exists, repository will end up in detached head state.

Also, checking out any tag will put repository in detached head state.


``ingit merge``
----------------

TODO: Write docs.


``ingit push``
----------------

TODO: Write docs.


``ingit gc``
----------------

Execute ``git gc --aggressive --prune``.


``ingit status``
----------------

Perform git status, as well as other diagnostic git commands.

Execute:

*   ``git status --short --branch`` to inform about any uncommited changes,
*   ``git log tracking_branch..branch`` to inform about commits that are not yet pushed to the remote,
*   ``git log branch..tracking_branch`` to inform about commits that are not yet merged from the remote.

Additionally, compare registered remotes with actual remotes to make sure that ingit
configuration is in sync with the repository metadata.

Use ``--ignored`` to include ignored files in the status report, just as with ``git status``.


Requirements
============

Python version 3.5 or later.

Python libraries as specified in `<requirements.txt>`_.

Building and running tests additionally requires packages listed in `<test_requirements.txt>`_.

Tested on Linux, OS X and Windows.
