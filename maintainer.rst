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

Upgrading dependencies
======================

- Update ``requirements.in``.

- Update ``requirements.txt`` using ``pip-compile`` from ``pip-tools``::

    pip-compile requirements.in

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
      --prefix mixed \
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
