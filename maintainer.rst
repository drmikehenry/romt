******************
Maintainer's notes
******************

These notes are intended for use by the maintainer.

Install ``uv``
==============

- Install ``uv`` globally, perhaps as documented at:
  https://docs.astral.sh/uv/getting-started/installation/

Building an executable with PyInstaller
=======================================

- Use the Nox ``build`` session::

    uv run nox -s build

Making a release
================

Perform these steps on Linux.

- Verify proper ``version = "x.y.z"`` in ``pyproject.toml``.

- Verify changes are recorded in ``CHANGES.rst``.

- Verify all Nox tests are passing::

    uv run nox

- Prepare the release::

    uv run nox -s release

- Follow on-screen instructions to complete release.

Testing with fake crates
========================

- Create ``fake`` area::

    mkdir -p fake/{import,export}
    cd fake

- Create fake crates in ``orig/`` and serve them::

    # In fake/ directory:
    ../scripts/setup-fake-crates.py

    cd orig
    romt serve --port 9000

- Export testing::

    # In fake/export directory:

    rm -rf crates/ git/crates.io-index crates.tar.gz
    romt crate \
      --index-url http://127.0.0.1:9000/git/crates.io-index \
      --crates-url http://127.0.0.1:9000/crates/{crate}/{crate}-{version}.crate \
      init pull download pack

- Import testing::

    # In fake/import directory:

    rm -rf crates git/crates.io-index
    romt crate -v init-import
    romt crate -v config
    romt crate -v --archive ../export/crates.tar.gz import

Testing with fake crate INDEX
=============================

- Create ``fake`` area::

    mkdir -p fake/{import,export}

- Export testing::

    # In fake/export directory:
    # Keep crates/ directory by default (save re-downloading).

    rm -rf crates.tar.gz fake-index git/crates.io-index
    ../../scripts/setup-fake-index.sh
    romt crate init --index-url fake-index
    romt crate -v config
    # Each time: choose a step number for upstream and export:
    git -C fake-index branch --force master step1
    romt crate -v export

- Import testing::

    # In fake/import directory:
    # One-time import testing setup:

    rm -rf crates git/crates.io-index
    romt crate -v init-import
    romt crate -v config
    # Import each time:
    romt crate -v --archive ../export/crates.tar.gz import

Use specific versions of dependencies
=====================================

For use on an offline network with a PyPI mirror that may be somewhat out of
date, it's useful to run ``uv lock --upgrade`` on the offline network lock to
ensure all versions are available on that mirror.  The list of chosen versions
may then be exported and used to constrain the published ``uv.lock`` file to
old-enough versions.

- On offline network, lock via::

    uv lock --upgrade

- Export chosen versions via::

    uv export \
      --quiet \
      --format requirements-txt \
      --no-annotate \
      --no-hashes \
      --no-editable > constraints.txt

  This generates lines such as::

    altgraph==0.17.5
    anyio==4.12.1
    argcomplete==3.6.3
    ...

- Bring ``constraints.txt`` to the online network.

- Edit ``pyproject.toml`` and add the contents of ``constraints.txt`` as
  follows::

    [tool.uv]
    override-dependencies = [
        "altgraph==0.17.5",
        "anyio==4.12.1",
        "argcomplete==3.6.3",
        ...
    ]

- Lock the dependencies using these constraints::

    uv lock

  This generates a new ``uv.lock`` file with the correct versions.

- Remove the temporary ``override-dependencies`` section from ``pyproject.toml``
  and re-lock (to remove some noise from ``uv.lock``)::

    uv lock
