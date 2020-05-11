******************
Maintainer's notes
******************

These notes are intended for use by the maintainer.

Making a release
================

- Activate the ``romt`` virtual environment.

- Verify proper ``__version__`` in ``src/romt/cli.py``.

- Verify changes are recorded in ``CHANGES.rst``.

- On Linux, run:

  .. code-block:: sh

    ./prepare-release.sh

- Follow on-screen instructions to complete release.

Testing with fake crate INDEX
=============================

- Create ``fake`` area::

    mkdir -p fake/{import,export}

- Export testing::

    # In fake/export directory:
    # Keep crates/ directory by default (save re-downloading).

    rm -rf crates.tar.gz fake-index git/crates.io-index
    ~/projects/romt/scripts/setup-fake-index.sh
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
