******************
Maintainer's notes
******************

These notes are intended for use by the maintainer.

Development environment setup
=============================

- Ensure Python and Pip and installed.

- Create and activate a virtual environment for your platform:

  - Linux:

  .. code-block:: sh

    python -m venv envs/linux
    . envs/linux/bin/activate

  - Windows:

  .. code-block:: sh

    py -3 -m venv envs\windows
    envs\windows\Scripts\activate.bat

  - Mac:

  .. code-block:: sh

    python -m venv envs/darwin
    . envs/darwin/bin/activate

- Install Romt in development mode:

  .. code-block:: sh

    pip install -e ".[dev]"

Making a release
================

- Remove these directories to force a clean build::

    dist/
    build/

- Verify proper ``__version__`` in ``src/romt/cli.py``.

- Build single-file executables using PyInstaller:

  .. code-block:: sh

    # On Linux:
    ./make-exec-linux.sh

    # On Windows:
    make-exec-windows.bat

    # On Mac:
    ./make-exec-darwin.sh

  Executables will be found at::

    dist/linux/romt
    dist/windows/romt.exe
    dist/darwin/romt

- Build source egg and wheel:

  .. code-block:: sh

    python setup.py -q sdist bdist_wheel

  Resulting egg and wheel are at::

    dist/romt-X.Y.Z-py3-none-any.whl
    dist/romt-X.Y.Z.tar.gz

- Check the artifacts:

  .. code-block:: sh

    twine check dist/romt-X.Y.Z*

- Upload to PyPI (both the ``.tar.gz`` and ``.whl``):

  .. code-block:: sh

    twine upload dist/romt-X.Y.Z*

- Create tag for version ``X.Y.Z``:

  .. code-block:: sh

    git tag -am 'Release vX.Y.Z.' vX.Y.Z

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
