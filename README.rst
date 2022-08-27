.. role:: bash(code)
    :language: bash

.. role:: json(code)
    :language: json

.. role:: python(code)
    :language: python


=====
ingit
=====

Tool for managing a large collection of repositories in git.

.. image:: https://img.shields.io/pypi/v/ingit.svg
    :target: https://pypi.org/project/ingit
    :alt: package version from PyPI

.. image:: https://github.com/mbdevpl/ingit/actions/workflows/python.yml/badge.svg?branch=main
    :target: https://github.com/mbdevpl/ingit/actions
    :alt: build status from GitHub

.. image:: https://codecov.io/gh/mbdevpl/ingit/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/mbdevpl/ingit
    :alt: test coverage from Codecov

.. image:: https://api.codacy.com/project/badge/Grade/477a1bc423f9465bb1ba8caeb895385b
    :target: https://app.codacy.com/gh/mbdevpl/ingit
    :alt: grade from Codacy

.. image:: https://img.shields.io/github/license/mbdevpl/ingit.svg
    :target: NOTICE
    :alt: license

If you have 100 git-versioned projects, keeping tabs on everything can be quite troublesome.

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
*   ``ingit register`` will add an existing git repository to ingit configuration;
*   ``ingit foreach`` will execute a custom command for each repository.


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
as well as ``ingit summary`` and ``ingit foreach``,
by default operate on all registered repositories.

However, they all can take the options ``--regex``/``-r`` and ``--predicate``/``-p``
that filter out the repositories using repository metadata (i.e. name, tags, path and remotes)
which is stored in the repositories configuration.

If both ``--regex``/``-r`` and ``--predicate``/``-p`` are provided,
predicate is applied first.


Filtering repositories by regular expression
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``--regex``/``-r`` option accepts any regular expression (also a simple string)
and filters the repos by trying to simply find a match in any of the metadata.

Specifically, ingit will forward your input regular expression into this function:

.. code:: python

    def regex_predicate(regex, name, tags, path, remotes):
        return (
            re.search(regex, name) is not None
            or any(re.search(regex, tag) is not None for tag in tags)
            or re.search(regex, str(path)) is not None
            or any(re.search(regex, name) for name, url in remotes.items()))

The actual implementation is here: `<ingit/runtime.py#L24>`_


Filtering repositories by predicate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``--predicate``/``-p`` option accepts a python boolean expression which will be inserted
into a predicate function template, as below:

.. code:: python

    lambda name, tags, path, remotes: (predicate)

The actual implementation is here: `<ingit/main.py#L266>`_

Therefore, executing ``ingit --predicate "'python' in tags" fetch`` results
in the following predicate being applied:

.. code:: python

    lambda name, tags, path, remotes: ('python' in tags)

And thus only repositories that have ``'python'`` in their tags are fetched.


Configuration
-------------

Ingit works based on configuration in 2 JSON files:

*   runtime configuration
*   repositories configuration

If either of the files doesn't exist, defaults will be generated.

The default paths to the files can be overridden via ``--config`` and ``--repos``
command-line options.


Runtime configuration
~~~~~~~~~~~~~~~~~~~~~

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


Repositories configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

It's a file that lists all registered projects and keeps their metadata.

It is automatically updated when ``ingit register`` is used.

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

Entry of each repository is a JSON object that can have the following fields:

.. code:: json

    {
      "name": "name of the project",
      "path": "path doesn't have to be specified, by default it will be 'repos_path/name'",
      "paths": {
        "machine name 1": "path used only on machine 1",
        "machine name 2": "path used only on machine 2",
        "": "if no machine name is given, the path is used in all other cases"
      },
      "remotes": {
        "remote name 1": "url 1",
        "remote name 2": "url 2"
      },
      "tags": [
        "tags are completely optional",
        "but repositories are much easier to manage if they are consistently tagged"
      ]
    }


The ``repos_path`` mentioned above is taken from the runtime configuration of ingit.

At most one of ``path`` or ``paths`` is allowed for each repo.

The two path specifications below are equivalent:

.. code:: json

    {
      "name": "name of the project",
      "path": "some path"
    }

.. code:: json

    {
      "name": "name of the project",
      "paths": {
        "": "some path"
      }
    }



Command details
===============

Below, details of each command are described.


``ingit summary``
-----------------

Show summary of registered repositories and status of configured repository root.

First of all, print a list of registered repositories. By default, all
registered repositories are listed, but, as in case of most commands, the
results can be filtered via a predicate or regex.

Independently, print a list of all unregistered repositories and all not
versioned paths present in the configured repositories root.


``ingit register``
------------------

Start tracking a repository in ingit.

.. code:: bash

    ingit register [PATH] [--tags TAG ...]

The initial configuration is set according to basic repository information:
its root directory name becomes "name" and its currently configured remotes
become "remotes". You can edit the configuration manually afterwards.

The final "path" to the repository stored in the configuration depends on the
``repos_path`` in runtime configuration. The configured "path" will be:

*   resolved absolute path if there is no ``repos_path`` configured or
    repository path is outside of the ``repos_path``;
*   resolved relative path to the ``repos_path``, if the repository path is
    within it;
*   nothing (i.e. not stored) if the if the repository is stored directly in
    ``repos_path`` (i.e. there are no intermediate directories).

Behaviour of storing relative/no paths in some cases is implemented to make
configuration file much less verbose in typical usage scenarios. To prevent
this behaviour, and force all repository paths to be absolute, simply set the
``repos_path`` in your runtime configuration to JSON ``null``.

Use ``PATH`` to provide the path to root directory of repository.
If not provided, current working directory is used.

Use ``--tags`` to provide tags for this repository, they will be added to the
initial configuration. Tags have no other effect than making repository
filtering easier.


``ingit foreach``
------------------

The given command is executed in a shell in working directory of each
project.

Use ``--timeout`` to set timeout of the command (in seconds).


``ingit clone``
---------------

Execute ``git clone <remote-url> --recursive --origin <remote-name> <path>``,
where values of ``<path>`` and ``<remote-...>`` are taken from default remote
configuration of the repository.

After cloning, add all remaining configured remotes to the repository and
fetch them.

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
``git clone https://github.com/spack/spack.git --recursive --origin source ~/Software/Spack``
because ``source`` is the first configured remote.
The subsequent commands will be ``git remote add github git@github.com:mbdevpl/spack.git``
and ``git fetch github``.


``ingit init``
--------------

Execute ``git init`` followed by ``git remote add`` for each configured
remote.


``ingit fetch``
---------------

Execute ``git fetch <remote-name>``, where the remote name is the remote of
the current tracking branch, or all remotes of the repository if there's no
tracking branch, or repository is in detached head state.

Use ``--all`` to fetch all remotes in all cases.


``ingit checkout``
------------------

Interactively select revision to checkout from list of local branches, remote
non-tracking branches and local tags.

The list of branches to select from is composed by combining:

*   local branches
*   non-tracking branches on all remotes
*   local tags

Checking out a remote branch will create a local branch with the same unless
it already exists. If it already exists, repository will end up in detached
head state.

Also, checking out any tag will put repository in a detached head state.


``ingit merge``
---------------

**Not yet implemented!** The following functionality is intended.

Interactively merge all branches to their tracking branches. For each not
merged ``<branch>``-``<tracking-branch>`` pair, execute
``git checkout <branch>`` and then if the merge is fast-forward,
automatically execute ``git merge <tracking-branch> --ff-only``. If not, then
show more information about the situation of the repository, and propose:

*   ``git merge --log <tracking-branch>``,
*   ``git rebase -i <tracking-branch>`` and
*   ``git reset --hard <tracking-branch>``.

If repository is dirty when this command is executed, do nothing. After work
is done, return to the originally checked-out branch.


``ingit push``
--------------

Execute ``git push <remote-name> <branch>:<tracking-branch-name>`` for the
active branch.

The above functionality works, but the following functionality is **not yet implemented**.

Use ``--all`` to execute the push for every branch that has a remote tracking
branch.


``ingit gc``
------------

Execute ``git gc --aggressive --prune``.


``ingit status``
----------------

Perform git status, as well as other diagnostic git commands.

Execute:

*   ``git status --short --branch`` to inform about any uncommitted changes,
*   ``git log tracking_branch..branch`` to inform about commits that are not
    yet pushed to the remote,
*   ``git log branch..tracking_branch`` to inform about commits that are not
    yet merged from the remote.

Additionally, compare registered remotes with actual remotes to make sure
that ingit configuration is in sync with the repository metadata.

Use ``--ignored`` to include ignored files in the status report, just as with
``git status``.


Requirements
============

Python version 3.8 or later.

Python libraries as specified in `<requirements.txt>`_.

Building and running tests additionally requires packages listed in `<requirements_test.txt>`_.

Tested on Linux, macOS and Windows.
