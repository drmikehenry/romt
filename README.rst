*******************************
ROMT - Rust Offline Mirror Tool
*******************************

Romt (Rust Offline Mirror Tool) aids in using the Rust programming language in
an offline context.  Instructions and tooling are provided for:

- Mirroring of Rust ecosystem artifacts:

  - Toolchains (Rustc, Cargo, libraries, etc.)
  - Rustup (toolchain multiplexer)
  - Crates.io (community-supplied Crates)

- Incremental artifact downloading (with a configurable number of simultaneous
  download jobs).

- Incremental artifact transfer to offline network.

- Artifact serving in offline context (offline computer, disconnected network).

Scenarios
=========

Romt support two main mirroring scenarios:

- Development laptop scenario:  Download Rust artifacts to the laptop when
  connected to the Internet, then serve the artifacts from the laptop when
  offline.

- Disconnected network scenario:  Download Rust artifacts on an
  Internet-connected "Export" machine, transfer them to an offline network, then
  serve the artifacts from an offline "Import" machine.

Instructions are provided for serving the artifacts using Romt itself via
unencrypted HTTP or via the nginx web server.

Alternative Tooling
===================

- Panamax is an alternative to Romt, written in Rust:
  https://github.com/panamax-rs/panamax

Requirements
============

- Python 3.8+ for running ``romt`` (requires some packages from pypi.org).
- Git is required for manipulating the crates.io-index repository.
- Internet-connected computer for initial downloading (Linux, Windows, Mac
  [#]_).
- Offline computer for serving artifacts (Linux, Windows, Mac).
- [Optional] Gnu Privacy Guard (GPG), if installed, is used used for signature
  checking.

.. [#] Note: the author does not have access to a Mac, so support for Romt on
   Mac is untested but hopefully close to working.  Pull requests for
   Mac-specific fixes are welcome.

Romt installation
=================

.. note::

  Take note of the instructions for upgrading from Romt versions before 0.4.0
  if you have existing crate mirrors created from older Romt versions.

Install prerequisites
---------------------

First install prerequisites for Romt:

- Ensure Git is installed; it is required for proper manipulation of the
  crates.io-index repository.

- For signature checking, GNU Privacy Guard (gpg) should be installed as well.
  If gpg is not available, signature files (``*.asc``) will still be transferred
  but signature checking will be skipped.

Next, choose an option for installation of Romt itself.

Option 1: Install a pre-built executable
----------------------------------------

The simplest method of installation is to use a pre-built self-contained
executable from the Github release area:
https://github.com/drmikehenry/romt/releases

Option 2: Install from Python Package Index
-------------------------------------------

Romt is also available in the Python Package Index (PyPI).  For machines with
direct Internet access, installation is straightforward; for machines on a
disconnected network, more steps are required.

First ensure that the ``PATH`` contains the directory that holds installed
Python packages::

    # For Linux:
    ~/.local/bin

    # For Windows with Python version X.Y:
    %APPDATA%\Python\PythonXY\Scripts

Next, choose installation method based on access to the Internet:

- With direct Internet access:

  - Install directly from PyPI:

    .. code-block:: sh

      pip install --user romt

- On a disconnected Network:

  - Download ``romt`` with dependencies (from Internet-connected machine):

    .. code-block:: sh

      mkdir romt
      cd romt
      pip download romt

  - Transfer the ``romt`` directory to a machine on the disconnected network.

  - Install from the ``romt`` directory:

    .. code-block:: sh

      cd romt
      pip install --user --no-index --find-links . romt

Option 3: Work with source
--------------------------

If desired, the source may be cloned from Github and installed into a virtual
environment.

- Install Poetry globally as described in the documentation:
  https://python-poetry.org/docs/#installation

- Clone source:

  .. code-block:: sh

    git clone https://github.com/drmikehenry/romt
    cd romt

- Run a Poetry shell (which creates and activates a virtual environment
  installed with Romt and all dependencies)::

    poetry shell

- Optionally build an executable for your platform:

  - Linux:

  .. code-block:: sh

    ./make-exec-linux.sh

  - Windows:

  .. code-block:: sh

    make-exec-windows.bat

  - Mac:

  .. code-block:: sh

    ./make-exec-darwin.sh

  Find executables at::

    dist/linux/romt
    dist/windows/romt.exe
    dist/darwin/romt

Romt usage overview
===================

Romt is a Python-based command-line tool with several commands:

- ``romt toolchain``: mirror and manage Rust toolchains.
- ``romt rustup``: mirror and manage Rustup.
- ``romt crate``: mirror and manage crate files from crates.io.
- ``romt serve``: simple HTTP server for toolchains, rustup, and crates.

See ``romt --help`` for overall usage help.

In particular, note that ``romt --readme`` will display the contents of this
README file for reference.

Quick-start development-laptop server
=====================================

For the development-laptop scenario, follow these steps to get a working server
configuration with mirrored Rust content.

- Ensure the laptop has Internet access.

- Install Romt (as above).

- Create area for mirrored artifacts:

  .. code-block:: sh

    mkdir mirror
    cd mirror

- Download latest stable toolchain:

  .. code-block:: sh

    # Change ``linux`` to ``windows`` or ``darwin`` as appropriate:
    romt toolchain -v -s stable -t linux download

- Download latest stable rustup version:

  .. code-block:: sh

    # Change ``linux`` to ``windows`` or ``darwin`` as appropriate:
    romt rustup -v -s stable -t linux download

- Setup crate mirror (one-time only):

  .. code-block:: sh

    romt crate init

- Download full crates.io mirror:

  .. code-block:: sh

    romt crate -v --keep-going update

  .. note::

    A few crates have been removed from crates.io and are therefore not
    available, so a few download failures (``403 Client Error: Forbidden``)
    should be expected.  The ``--keep-going`` option allows romt to continue
    in the face of these missing crates.

    Currently (April 2022), versions of the following crates are missing:

    - bork
    - css-modules
    - css-modules-macros
    - deploy
    - doccy
    - etch
    - glib-2-0-sys
    - glue
    - gobject-2-0-sys
    - peek
    - pose

- Configure crate mirror to be served from localhost (one-time only):

  .. code-block:: sh

    romt crate config

- Start Romt as a server on http://localhost:8000:

  .. code-block:: sh

    romt serve

  .. note::

    Leave the server running in this dedicated terminal.

Quick-start disconnected-network server
=======================================

Setting up a server for the disconnected-network scenario is similar to that for
the development-laptop scenario above; explanations that overlap that scenario
are omitted below.

- On Internet-connected Export machine:

  - Install Romt (as above).

  - Create area for mirrored artifacts:

    .. code-block:: sh

      mkdir mirror
      cd mirror

  - Download latest stable toolchain and create ``toolchain.tar.gz``:

    .. code-block:: sh

      # Change ``linux`` to ``windows`` or ``darwin`` as appropriate:
      romt toolchain -v -s stable -t linux download pack

  - Download latest stable rustup version and create ``rustup.tar.gz``:

    .. code-block:: sh

      # Change ``linux`` to ``windows`` or ``darwin`` as appropriate:
      romt rustup -v -s stable -t linux download pack

  - Setup crate mirror (one-time only):

    .. code-block:: sh

      romt crate init

  - Download and create ``crates.tar.gz``:

    .. code-block:: sh

      romt crate -v --keep-going export

  - Transfer ``toolchain.tar.gz, ``rustup.tar.gz``, and ``crates.tar.gz`` to
    Import machine.

- On Disconnected network Import machine:

  - Install Romt (as above).

  - Create area for mirrored artifacts (one-time only):

    .. code-block:: sh

      mkdir mirror

  - Place exported ``toolchain.tar.gz, ``rustup.tar.gz``, and ``crates.tar.gz``
    files into this ``mirror/`` directory, and enter the directory at a prompt:

    .. code-block:: sh

      cd mirror

  - Import toolchain and rustup:

    .. code-block:: sh

      romt toolchain -v unpack
      romt rustup -v unpack

  - Setup crate mirror (one-time only):

    .. code-block:: sh

      romt crate init-import

  - Import ``crates.tar.gz``:

    .. code-block:: sh

      romt crate -v --keep-going import

  - Configure crate mirror to be served from localhost (one-time only):

    .. code-block:: sh

      romt crate config

  - Start Romt as a server on http://localhost:8000:

    .. code-block:: sh

      romt serve

    .. note::

      Leave the server running in this dedicated terminal.

Quick-start client setup
========================

Follow these steps to configure Rust tooling for use with a mirror server on
localhost using either Quick-start server configuration above.

- Setup environment variables to point to the server.  By default, this will be
  at http://localhost:8000; adjust all uses of ``localhost:8000`` below for
  different server address:port combinations:

  .. code-block:: sh

    # For Linux/Mac:
    export RUSTUP_DIST_SERVER=http://localhost:8000
    export RUSTUP_UPDATE_ROOT=http://localhost:8000/rustup

    # For Windows:
    set RUSTUP_DIST_SERVER=http://localhost:8000
    set RUSTUP_UPDATE_ROOT=http://localhost:8000/rustup

  .. note::

    These variables must be set in each terminal window before using the mirror
    server.

- Download the ``rustup-init`` installer for your platform from the Romt server
  using the appropriate URL below, saving it into the current directory:

  - Linux:
    http://localhost:8000/rustup/dist/x86_64-unknown-linux-gnu/rustup-init

  - Windows:
    http://localhost:8000/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe

  - Mac:
    http://localhost:8000/rustup/dist/x86_64-apple-darwin/rustup-init

- Run the installer, accepting the defaults:

  .. code-block:: sh

    # Linux/Mac:
    chmod +x rustup-init
    ./rustup-init

    # Windows
    rustup-init

- Ensure environment changes take place in current shell:

  .. code-block:: sh

    # For Linux/Mac:
    source $HOME/.cargo/env

    # For Windows:
    PATH %USERPROFILE%\.cargo\bin;%PATH%

- Try out some rustup commands::

    rustup self update
    rustup component add rust-src

- Create the text file ``~/.cargo/config.toml``
  (``%USERPROFILE%\.cargo\config.toml`` on Windows) with the following content::

    [source.crates-io]
    registry = 'http://localhost:8000/git/crates.io-index'

    # Disable cert revocation checking (necessary only on Windows):
    [http]
    check-revoke = false

    # For greatly improved performance, have Cargo use the Git command-line
    # client to acquire `crates.io-index` repository. See
    # https://github.com/rust-lang/cargo/issues/9167 for details.
    [net]
    git-fetch-with-cli = true

- Create a sample project to demonstrate crate usage:

  .. code-block:: sh

    cargo new rand_test
    cd rand_test

- Append the following line to ``Cargo.toml`` (just below the
  ``[dependencies]`` line)::

    rand = ""

- Fetch ``rand`` and its dependencies::

    cargo fetch

Upgrading from Romt versions before 0.4.0
=========================================

When upgrading Romt, it's recommended to use the same version of Romt on both
the Internet-connected and offline hosts.

Romt 0.4.0 changes how crate files are stored on-disk by default, in order to
fix problems using a mirror with case-sensitive and case-insensitive filesystems
simultaneously.  Older Romt stores crates in directories based on the prefix of
each crate's mixed-case name (e.g., ``MyCrate-0.1.0.crate`` would have a prefix
of ``My/Cr/``).  This works for filesystems that are either case-sensitive or
case-insensitive, but it does not allow a tree of crate files created with one
case sensitivity to be accessed using the opposite case sensitivity.  Romt 0.4.0
now defaults to making prefix directories in lowercase, allowing a crate mirror
to be used via arbitrary case sensitivity.

For backward compatibility, Romt 0.4.0 supports the use of existing mirror trees
transparently.  Newly created mirror trees will use lowercase prefixes by
default (usable on all filesystems); mixed-case prefixes may be requested via
the ``--prefix=mixed`` flag (permitted only with case-sensitive filesystems).

Romt 0.4.0 generates crate archives (``crates.tar.gz``) using mixed-case
prefixes by default for backward compatibility, but it can also use lowercase
prefixes for consistency with the preferred on-disk prefix format.  To
distinguish the prefix style, Romt 0.4.0 adds an ``ARCHIVE_FORMAT`` file to the
crate archive.  Format ``1`` is compatible with old Romt except for the addition
of the ``ARCHIVE_FORMAT`` file.  Old Romt will see this file as an error and
refuse to unpack the archive by default, but processing will succeed using the
invocation ``romt crate unpack --keep-going``.  To avoid corrupting
an existing crate mirror by unpacking a new crate archive with old Romt,
new archives currently default to format ``1``, but it's recommended to upgrade
Romt to ensure proper processing of all crate archive formats.

Converting crate mirror to lowercase prefixes
---------------------------------------------

To convert an existing crate mirror (using mixed-case prefixes) to the new
format (using lowercase prefixes), the easiest method is to make a crate archive
of the old mirror, then unpack the archive using the new format.  For example:

.. code-block:: sh

  # Pack up existing crate mirror into ``crates.tar.gz``:
  romt crate -v --keep-going --start 0 --end master pack

  # Rename the old crate tree out of the way:
  mv crates crates.old

  # Initialize for importing with a temporary index area:
  romt crate --index index-tmp init-import

  # Unpack crates from crates.tar.gz into new crates/ tree:
  romt crate -v --index index-tmp unpack

  # Verify conversion:
  romt crate verify -v --start 0

  # Cleanup:
  rm -rf index-tmp crates.old

Note that the above steps eliminate the unpredictable-case prefixes that are
created with old Romt using a case-insensitive filesystem (such as on Windows).

Commonalities
=============

Romt has some features that are shared across two or more commands.

TARGET
------

The TARGET specifies the platform for executables using standard tuple values
(e.g., ``x86_64-unknown-linux-gnu``).  Any tuples supported by Rust are valid.
Typical values are shown below; in parentheses are aliases Romt provides for
ease of typing these common targets:

- ``x86_64-unknown-linux-gnu`` (alias ``linux``)
- ``x86_64-pc-windows-msvc`` (alias ``windows``)
- ``x86_64-apple-darwin`` (alias ``darwin``)

TARGET values are given by the option ``--target TARGET``.  Multiple TARGET
options may be given, and each TARGET will be split at commas and whitespace to
produce a list of desired TARGET values, e.g.::

  --target linux,windows --target 'darwin i686-pc-windows-msvc'

A TARGET may be a literal ``all`` that expands to all known targets.  For ``romt
toolchain``, this list comes from the manifest file.  For ``romt rustup``, it
comes from a hard-code list within Romt; this is an ever-changing list that may
be out-of-date in an old release of Romt.

A TARGET may be a literal ``*`` (asterisk) that expands to all targets with at
least one on-disk file for the given SPEC.

SHA256 hashes
-------------

- Each file named ``{file}.sha256`` contains the SHA256 hash of the
  corresponding file named ``{file}``.  Romt verifies all hashes to ensure file
  integrity.

Command-line option details
---------------------------

- The option ``--num-jobs`` controls how many simultaneous download jobs Romt
  may use at a time.  By default, ``--num-jobs=4``, which should be a
  conservative value that won't stress the servers heavily.

- The option ``--timeout`` controls the timeout in seconds for downloading.
  A value of zero disables the timeout functionality altogether.

- The option ``--assume-ok`` instructs Romt that all files already on-disk are
  to be assumed OK; no hashes or signatures are checked for such files.

``toolchain`` operation
=======================

The ``toolchain`` operation deals with Rust toolchains.

SPEC
----

Each toolchain is identified by a SPEC value which takes on one of the below
forms::

  {channel}
  {channel}-{date}
  {date}

In the above SPEC forms:

- ``{channel}`` is typically one of the channel names ``nightly``, ``beta``,
  ``stable``.  It may also be a version number of the form ``X.Y.Z`` or a
  literal ``*`` (asterisk) as a wildcard that expands to the set
  ``nightly,beta,stable``.

- ``{date}`` is typically of the form ``YYYY-MM-DD`` (e.g., ``2020-04-30``).  It
  may also be a literal ``*`` (asterisk) as a wildcard that expands to all
  toolchain dates on-disk, or a literal ``latest`` that expands to the most
  recent toolchain date on-disk.

- Note that a SPEC value consisting of a single ``*`` represents a wildcarded
  ``{date}`` value, not a ``{channel}`` value.  It is equivalent to ``*-*``
  (making both ``{channel}`` and ``{date}`` wild).

- Wildcards (``*`` and ``latest``) may not be used when downloading, and the
  ``{channel}`` is always required.  The ``{date}`` field may be omitted to
  download the most recent toolchain for the given channel.

- SPEC values are given by the option ``--select SPEC``.  Multiple SPEC options
  may be given, and each SPEC will be split at commas and whitespace to produce
  a list of desired SPEC values.  E.g.::

    --select nightly,stable --select beta-2020-01-23

TARGET
------

See the TARGET section of Commonalities above for details.

Manifest file
-------------

A manifest file provides details about a toolchain for a given SPEC, enumerating
valid combinations of toolchain components and targets.

The manifest filename is of the form ``channel-rust-{channel}.toml``, where
``{channel}`` is one of ``nightly``, ``beta``, or ``stable``.  For ``stable``
manifests, the manifest is duplicated into a file of the form
``channel-rust-{version}.toml``, where ``{version}`` is a version number of the
form ``X.Y.Z``.

Downloading
-----------

Downloading is requested via the ``romt toolchain download`` command.

A toolchain is specified by a SPEC/TARGET pair.  Both must be given.
Wildcarding (via ``*`` or ``latest``) is not permitted, though the ``{date}``
may be omitted from the SPEC value, and TARGET may be the literal ``all`` to
download all known targets for the SPEC.

By default, all toolchain components will be downloaded; but when the switch
``--cross`` is supplied, only the Rust standard library component ``rust-std``
will be downloaded.  This is to support cross-compilation to a given target
without the need to download all toolchain components for that target.

Files are downloaded from ``https://static.rust-lang.org/dist`` by default; this
may be changed via the option ``--url <URL>``.

Files are downloaded to the destination directory ``dist/`` by default; this
may be changed via the option ``--dest DEST``.

When downloaded, the toolchain will be stored on-disk in the following layout::

  dist/
    YYYY-MM-DD/
      channel-rust-{channel}.toml
      channel-rust-{channel}.toml.asc
      channel-rust-{channel}.toml.sha256
      {component}-{channel}.tar.xz
      {component}-{channel}.tar.xz.asc
      {component}-{channel}.tar.xz.sha256
      {component}-{channel}-{target}.tar.xz
      {component}-{channel}-{target}.tar.xz.asc
      {component}-{channel}-{target}.tar.xz.sha256

Where:

- ``YYYY-MM-DD`` is the toolchain date.
- ``{channel}`` is one of ``nightly``, ``beta``, or ``stable``.
- ``{component}`` represents a toolchain component (e.g., ``rust``, ``cargo``,
  ``rust-src``).
- ``{target}`` represents a target tuple (e.g., ``x86_64-unknown-linux-gnu``).
  Components lacking a ``{target}`` are common across all targets; currently
  this is limited to the ``rust-src`` component.

- Each file named ``{file}.asc`` contains the Gnu Privacy Guard (GPG) digital
  signature of the corresponding file named ``{file}``.  Checking signature
  requires GPG; if it is not installed, signature files won't be checked but
  they will still be transferred.  The verification key is available at
  https://static.rust-lang.org/rust-key.gpg.ascii; this key is built into Romt
  itself for offline use.

For example, after downloading with this command:

.. code-block:: sh

  romt toolchain download --select nightly-2020-04-30 --target linux

The tree would contain (among other files)::

  dist/
    2020-04-30/
      channel-rust-nightly.toml
      channel-rust-nightly.toml.asc
      channel-rust-nightly.toml.sha256
      rust-src-nightly.tar.xz
      rust-src-nightly.tar.xz.asc
      rust-src-nightly.tar.xz.sha256
      rust-nightly-x86_64-unknown-linux-gnu.tar.xz
      rust-nightly-x86_64-unknown-linux-gnu.tar.xz.asc
      rust-nightly-x86_64-unknown-linux-gnu.tar.xz.sha256

For convenience, the most recently released toolchain for each channel
(``nightly``, ``beta``, or ``stable``) will be copied directly into the
``dist/`` directory.  This is especially helpful for ``stable`` and ``beta``
builds so that the date of the most recent release need not be known in advance.
For ``stable`` manifests, the version-specific copy of the manifest is placed
into ``dist/`` as well.

For example, as of 2020-05-06, the most recent manifests were for SPEC values
of:

- ``nightly-2020-05-06``
- ``beta-2020-04-26``
- ``stable-2020-04-23`` (version ``1.43.0``)

On that date, performing a download with ``--target linux`` and ``--select
nightly,beta,stable`` would yield the following downloaded manifests::

  dist/
    channel-rust-beta.toml
    channel-rust-nightly.toml
    channel-rust-stable.toml
    channel-rust-1.43.0.toml
    2020-04-23/
      channel-rust-stable.toml
      channel-rust-1.43.0.toml
    2020-04-26/
      channel-rust-beta.toml
    2020-05-06/
      channel-rust-nightly.toml

Where the dateless manifests housed directly in ``dist/`` are copies of those
from the dated directories.

Because the contents of dateless manifests are subject to change, cached copies
of these files are re-downloaded during a ``download`` command.

Packing/unpacking
-----------------

Downloaded toolchains may be packed into an ``ARCHIVE`` file using the ``romt
toolchain pack`` command.

The archive file may be moved to another machine and unpacked using the ``romt
toolchain unpack`` command.

Romt will detect when a toolchain has been downloaded via the ``--cross``
switch, in which case only the ``rust-std`` component (along with whatever other
toolchain components are present, if any) will be processed.

For both ``pack`` and ``unpack``, the ``ARCHIVE`` file is named
``toolchain.tar.gz`` by default; this may be changed via the option ``--archive
ARCHIVE``.

An ``unpack`` command automatically performs a ``verify`` (described below).  In
addition, dateless manifests are reconstructed automatically during ``unpack``
as part of a fixup operation (described below).

An archive file contains files from dated subdirectories only.  Given the
example above for the ``download`` command, the ``ARCHIVE`` would contain only
these manifests::

  dist/
    2020-04-23/
      channel-rust-stable.toml
    2020-04-26/
      channel-rust-beta.toml
    2020-05-06/
      channel-rust-nightly.toml

Fixup
-----

Each toolchain identified by a SPEC has a canonical manifest file stored in the
toolchain's dated directory.  This file has a path of the form
``YYYY-MM-DD/channel-rust-{channel}.toml``, where ``{channel}`` is one of the
channel names ``nightly``, ``beta``, or ``stable``.

The "fixup" operation is responsible for making any necessary copies of each
canonical manifest in the ``dist/`` tree.  If the given on-disk manifest is
found in the latest dated directory, it will be copied into the top-level
``dist/`` directory.  In addition, for each SPEC on the ``stable`` channel a
version-specific manifest file of the form ``channel-rust-X.Y.Z.toml`` will be
copied into the dated directory and the top-level ``dist/`` directory.

A fixup operation may be explicitly requested via the ``romt toolchain fixup``
command, though that should rarely be required because it is automatically
performed after any ``download`` or ``unpack`` command.

Consider the example above for the ``download`` command; it would generate an
archive containing only these canonical manifests::

  dist/
    2020-04-23/
      channel-rust-stable.toml
    2020-04-26/
      channel-rust-beta.toml
    2020-05-06/
      channel-rust-nightly.toml

The ``fixup`` command would copy these manifests to create::

  dist/
    channel-rust-beta.toml
    channel-rust-nightly.toml
    channel-rust-stable.toml
    channel-rust-1.43.0.toml
    2020-04-23/
      channel-rust-stable.toml
      channel-rust-1.43.0.toml
    2020-04-26/
      channel-rust-beta.toml
    2020-05-06/
      channel-rust-nightly.toml

Listing downloaded toolchains
-----------------------------

The ``romt toolchain list`` command prints information about on-disk toolchains
for the provided SPEC values.  Wildcards are permitted.

For example, the most recent on-disk ``stable`` release can be shown via:

.. code-block:: sh

  romt toolchain list --select 'stable-latest'

With example output::

  stable-2024-02-08(1.76.0)    targets[10/94]   packages[34/425]
    x86_64-unknown-linux-gnu                      native-target
    x86_64-unknown-linux-musl                     cross-target

Next to each target name is that target's "type", one of:

- ``native-target`` (a full toolchain)
- ``cross-target`` (a toolchain for cross-compilation)
- ``minimal`` (minimal toolchain components with no compilation support)

A ``native-target`` contains a full toolchain capable of running on the target
natively (and compiling Rust code to that target as well).

A ``cross-target`` does not contain a compiler that runs on the target; but it
does contain the Rust standard library component ``rust-std`` for the target,
enabling cross-compilation to the target (using a ``native-target`` toolchain on
another host).

A ``minimal`` target lacks ``rust-std`` but has some minimal components
available.  Typically a minimal target shows up by coincidence because it shares
one or more components with another target.  For example, at the time of this
writing the minimal target ``mips-unknown-linux-gnu`` has no components of its
own in toolchain 1.76.0, but it shares the component ``rust-docs`` with the more
common target ``x86_64-unknown-linux-gnu``; therefore, downloading the full
toolchain for ``x86_64-unknown-linux-gnu`` will cause ``mips-unknown-linux-gnu``
to be present as a minimal toolchain.

Because most ``minimal`` targets are present only by coincidence and not useful,
listing them is suppressed by default.  Use ``--verbose`` to include them,
e.g.::

.. code-block:: sh

  romt toolchain list --select 'stable-latest' --verbose

With example output::

  List: stable-2024-02-08
  [verify] dist/2024-02-08/channel-rust-stable.toml
  stable-2024-02-08(1.76.0)    targets[10/94]   packages[34/425]
    mips-unknown-linux-gnu                        minimal
    mips64-unknown-linux-gnuabi64                 minimal
    mips64el-unknown-linux-gnuabi64               minimal
    mipsel-unknown-linux-gnu                      minimal
    mipsisa32r6-unknown-linux-gnu                 minimal
    mipsisa32r6el-unknown-linux-gnu               minimal
    mipsisa64r6-unknown-linux-gnuabi64            minimal
    mipsisa64r6el-unknown-linux-gnuabi64          minimal
    x86_64-unknown-linux-gnu                      native-target
    x86_64-unknown-linux-musl                     cross-target

To suppress information about targets, use ``--quiet``:

.. code-block:: sh

  romt toolchain list --select 'stable-latest' --quiet

With example output::

  stable-2024-02-08(1.76.0)

With wildcards, Romt can provide a listing of all available toolchains for a
given channel:

.. code-block:: sh

  romt toolchain list -s 'nightly-*'

With example output::

  nightly-2024-02-14(1.78.0)   targets[9/94]    packages[54/486]
    x86_64-unknown-linux-gnu                      native-target
  nightly-2023-10-31(1.75.0)   targets[9/95]    packages[54/488]
    x86_64-unknown-linux-gnu                      native-target
  nightly-2023-07-04(1.72.0)   targets[5/96]    packages[53/529]
    x86_64-unknown-linux-gnu                      native-target

After toolchain importation, it may be useful to list toolchains for each
channel for reference:

.. code-block:: sh

  romt toolchain list -s 'nightly-*' > nightly.txt
  romt toolchain list -s 'beta-*' > beta.txt
  romt toolchain list -s 'stable-*' > stable.txt

``toolchain`` scenarios
-----------------------

For the laptop scenario, only the ``download`` command is needed.  After
downloading a toolchain, it will be available for serving via ``romt serve``
(or other means).  For example, to download the latest stable toolchain for
Linux:

.. code-block:: sh

    romt toolchain download --select stable --target linux

For the disconnected network scenario, toolchains are downloaded and packed on
an Internet-connected Export machine, then unpacked on an Import machine, e.g.:

- On the Export machine:

  - First, download the latest stable toolchain for Linux into a local ``dist/``
    directory and pack it into an archive for transfer:

    .. code-block:: sh

      romt toolchain download pack --select stable --target linux

  - Transfer the resulting ``toolchain.tar.gz`` file onto the Import machine.

- On the Import machine:

  - Unpack the archive into a local ``dist/`` directory:

    .. code-block:: sh

      romt toolchain unpack

Miscellaneous commands
----------------------

A few additional commands are provided for ``romt toolchain``.

``romt toolchain fetch-manifest`` is the same as ``download``, but only the
manifest is downloaded.

``romt toolchain verify`` validates the SHA256 hashes and GPG signatures of
on-disk toolchains.  It is implicitly done as part of ``download`` and
``unpack``.

``romt toolchain all-targets`` prints a list of all known targets mentioned in
the given SPEC.

Command-line option details
---------------------------

The option ``--warn-signature`` instructs Romt to treat signature failures as
warnings instead of as failures.  Signature files will still be downloaded and
transferred.  This might be helpful in case the signing key changes.

The option ``--no-signature`` prevents both downloading and checking of GPG
signature files (``*.asc``).  This is mainly for testing.

``rustup`` operation
====================

The ``rustup`` operation deals with the Rustup toolchain multiplexer.

SPEC
----

Each rustup version is identified by a SPEC value which takes on one of the
below forms::

  {version}
  stable
  latest
  *

In the above SPEC forms:

- ``{version}`` is a version number of the form ``X.Y.Z``.

- A literal ``stable`` refers to the current stable version given in the
  ``release-stable.toml`` file (described later).

- A literal ``*`` (asterisk) is a wildcard that expands to all on-disk versions.

- A literal ``latest`` is a wildcard that expands to the latest on-disk version.

- Wildcards (``*`` and ``latest``) may not be used when downloading, but
  ``stable`` is permitted.

- SPEC values are given by the option ``--select SPEC``.  Multiple SPEC options
  may be given, and each SPEC will be split at commas and whitespace to produce
  a list of desired SPEC values.  E.g.::

    --select stable,1.20.0 --select '1.19.0 1.20.1'

TARGET
------

See the TARGET section of Commonalities above for details.

Downloading
-----------

Downloading is requested via the ``romt rustup download`` command.

A rustup executable is specified by a SPEC/TARGET pair.  Both must be given.
Wildcarding (via ``*`` or ``latest``) is not permitted, though SPEC may be the
literal ``stable`` to download the latest stable release, and TARGET may be the
literal ``all`` to download all known targets for the SPEC.

Files are downloaded from ``https://static.rust-lang.org/rustup`` by default;
this may be changed via the option ``--url <URL>``.

Files are downloaded to the destination directory ``rustup/`` by default;
this may be changed via the option ``--dest DEST``.

When downloaded, files will be stored on-disk in the following layout::

  rustup/
    release-stable.toml
    archive/
      {version}/
        {target}/
          {rustup}
          {rustup}.sha256
    dist/
      {target}/

Where:

- ``release-stable.toml`` is a configuration file that indicates the most recent
  stable version of rustup.
- ``{version}`` is a rustup version of the form ``X.Y.Z``.
- ``{target}`` represents a target tuple (e.g., ``x86_64-unknown-linux-gnu``).
- ``{rustup}`` is the name of the rustup executable.  On most platforms, this is
  ``rustup-init``; on Windows, it's ``rustup-init.exe``.

For example, if version 1.21.1 were the most recent stable version, after
downloading with this command:

.. code-block:: sh

  romt rustup download --select stable --target linux

The tree would contain::

  rustup/
    release-stable.toml
    dist/
      x86_64-unknown-linux-gnu/
        rustup-init
        rustup-init.sha256
    archive/
      1.21.1/
        x86_64-unknown-linux-gnu/
          rustup-init
          rustup-init.sha256

For convenience, all targets found in the most recently released rustup version
will be copied directly into the ``rustup/dist/`` directory.

Because the ``release-stable.toml`` file is subject to change, this file will be
re-downloaded during a ``download`` command when SPEC is ``stable``.

Packing/unpacking
-----------------

Downloaded rustup executables may be packed into an ``ARCHIVE`` file using the
``romt rustup pack`` command.

The archive file may be moved to another machine and unpacked using the
``romt rustup unpack`` command.

For both ``pack`` and ``unpack``, the ``ARCHIVE`` file is named
``rustup.tar.gz`` by default; this may be changed via the option ``--archive
ARCHIVE``.

An ``unpack`` command automatically performs a ``verify`` (described below).  In
addition, the ``rustup/dist/`` tree is created automatically during ``unpack``
as part of a fixup operation (described below).

An archive file contains files from ``rustup/archive/{version}`` subdirectories
only.  Given the example above for the ``download`` command, the ``ARCHIVE``
would contain only these files::

  rustup/
    archive/
      1.21.1/
        x86_64-unknown-linux-gnu/
          rustup-init
          rustup-init.sha256

Fixup
-----

Each rustup version is stored in a directory of the form
``rustup/archive/{version}``.

The "fixup" operation is responsible for copying the most recent on-disk
rustup version to ``rustup/dist/``, and for updating
``rustup/release-stable.toml`` to contain the most recent version number.

A fixup operation may be explicitly requested via the ``romt rustup fixup``
command, though that should rarely be required because it is automatically
performed after any ``download`` or ``unpack`` command.

Consider the example above for the ``download`` command that generated the
following archive contents::

  rustup/
    archive/
      1.21.1/
        x86_64-unknown-linux-gnu/
          rustup-init
          rustup-init.sha256

Assuming this is the latest on-disk version, the ``fixup`` command would copy
``rustup/archive/1.21.1`` to ``rustup/archive`` as shown below, and it would
create ``release-stable.toml`` to point to version ``1.21.1``::

  rustup/
    release-stable.toml
    archive/
      1.21.1/
        x86_64-unknown-linux-gnu/
          rustup-init
          rustup-init.sha256
    dist/
      x86_64-unknown-linux-gnu/
        rustup-init
        rustup-init.sha256

Listing downloaded rustup versions
----------------------------------

The ``romt rustup list`` command prints information about on-disk rustup
versions for the provided SPEC values.  Wildcards are permitted.

For example, the most recent on-disk version can be shown via:

.. code-block:: sh

  romt rustup list --select 'latest'

With example output::

  List: 1.21.1
  1.21.1   targets[1]
    x86_64-unknown-linux-gnu

To suppress information about targets, use ``--quiet``:

.. code-block:: sh

  romt rustup list --select 'latest' --quiet

With example output::

  1.21.1

With wildcards, Romt can provide a listing of all available rustup versions:

.. code-block:: sh

  romt rustup list -s '*'

With example output::

  List: 1.21.1
  1.21.1   targets[1]
    x86_64-unknown-linux-gnu
  List: 1.21.0
  1.21.0   targets[1]
    x86_64-unknown-linux-gnu
  List: 1.20.0
  1.20.0   targets[1]
    x86_64-unknown-linux-gnu

``rustup`` scenarios
--------------------

For the laptop scenario, only the ``download`` command is needed.  After
downloading a rustup executable, it will be available for serving via ``romt
serve`` (or other means).  For example, to download the latest stable rustup for
Linux:

.. code-block:: sh

    romt rustup download --select stable --target linux

For the disconnected network scenario, rustup versions are downloaded and packed
on an Internet-connected Export machine, then unpacked on an Import machine,
e.g.:

- On the Export machine:

  - First, download the latest stable rustup for Linux into a local ``rustup/``
    directory and pack it into an archive for transfer:

    .. code-block:: sh

      romt rustup download pack --select stable --target linux

  - Transfer the resulting ``rustup.tar.gz`` file onto the Import machine.

- On the Import machine:

  - Unpack the archive into a local ``rustup/`` directory:

    .. code-block:: sh

      romt rustup unpack

Miscellaneous commands
----------------------

A few additional commands are provided for ``romt rustup``.

``romt rustup verify`` validates the SHA256 hashes of on-disk rustup
executables.  It is implicitly done as part of ``download`` and ``unpack``.

``romt rustup all-targets`` prints a list of all known targets in Romt's
hard-coded list.

``crate`` operation
====================

The ``crate`` operation deals with crates (community-written packages of Rust
source code) from the server https://crates.io.

Crates.io INDEX
---------------

Individual crates are indexed via a Git repository called INDEX.  By default,
INDEX is cloned from https://github.com/rust-lang/crates.io-index; this may be
changed with the option ``--index-url INDEX_URL``.

The INDEX contains one text file for each crate name, where each line of the
file is a JSON-formatted description of a single version of that crate.  When a
new crate file is uploaded, another line is appended to the file and a new
commit is made.

The on-disk INDEX directory defaults to ``git/crates.io-index``; it may be
changed via the option ``--index INDEX``.

INDEX branches
--------------

INDEX is essentially a standard Git clone with some additional conventions.
It uses the following branches:

- ``remotes/origin/master``

    The ``master`` branch of the ``origin`` repository.  Typically this is the
    repository on Github given by the default value of INDEX_URL.

- ``master``

    The local ``master`` branch.  This is based on ``remotes/origin/master``,
    with possible changes to the ``config.json`` file (described later).

- ``origin_master``

    A local convenience branch that tracks ``remotes/origin/master``.  This
    makes it easy to push ``master`` and ``remotes/origin/master`` to a server.

- ``mark``

    A branch for tracking progress (detailed later).

- ``working``

    A branch checked out to the working tree and used for merging and
    modifying repository content; changes are then published atomically to the
    ``master`` branch to avoid race conditions.

INDEX file structure
--------------------

To keep the number of files in each directory down to a manageable size, the
text files for each crate are distributed into subdirectories based on the first
few characters of the crate's name.  The path within INDEX for a crate named
``{crate}`` is given by ``{prefix}/{crate}``, where ``{prefix}`` is calculated
based on the length of the crate's name; variations exist for 1-, 2-, 3-, and
4-or-more characters:

=========  =================  =========================
{prefix}   crate name length  crate name (as lowercase)
=========  =================  =========================
1          1                  a
2          2                  ab
3/a        3                  abc
ab/cd      4 or more          abcd*
=========  =================  =========================

The directory names are based on the crate name converted to lowercase so that
the repository may be cloned on case-insensitive filesystems (such as on
Windows).

For example, the file for the ``serde`` crate would be found by default at
``git/crates.io-index/se/rd/serde``.

In addition to per-crate files, there is a ``config.json`` file in the INDEX
that configures the URL for downloading crate files.

INDEX range
-----------

A RANGE is defined by a START commit and an END commit.  The changes made to the
INDEX between START and END represent the list of crates in RANGE that were
uploaded to crates.io.

Because START and END represent Git commits, any valid Git commit reference may
be used.  In addition, START may be given the value ``0`` when there is no
starting commit, in which case all commits through END are in RANGE.

The START commit is selected via the option ``--start START``.

The END commit is selected via the option ``--end END``.

In general, START and END must both be valid commits in the INDEX; but because
Git branches can't refer to an empty commit, there is no way to initialize a
branch name to a value (like ``0``) that means "the start of the repository".
To handle this case, the option ``--allow-missing-start`` indicates that Romt
should treat an unknown branch name for START to be the same as ``0``.

Crate files
-----------

Crate files (``*.crate``) are tarballs containing Rust source code.  Filenames
follow the naming convention ``{crate}-{version}.crate``, where ``{crate}`` is
the name of the crate (e.g., ``serde``) and ``{version}`` is the crate's version
number in the form ``X.Y.Z``.

The URL for a given crate file is given by the template CRATES_URL.  The default
value is https://static.crates.io/crates/{crate}/{crate}-{version}.crate; it may
be changed with the option ``--crates-url CRATES_URL``.

For each crate, the CRATES_URL template will be expanded by replacing
``{crate}`` with the name of the crate and ``{version}`` with its version.  For
example, the default URL for version ``1.0.99`` of the ``serde`` crate would be:
https://static.crates.io/crates/serde/serde-1.0.99.crate

In addition, ``{prefix}`` and ``{lowerprefix}`` will be replaced with the
crate's prefix and lowercase prefix, respectively (where the construction of the
prefix is explained below).

As an alternative, to use the crate.io API for downloading crates, set
CRATES_URL to: https://crates.io/api/v1/crates/{crate}/{version}/download

CRATES_ROOT
-----------

Crate files (``*.crate``) are stored on-disk in a directory tree rooted at
CRATES_ROOT, which defaults to ``crates/`` and may be changed via the option
``--crates CRATES_ROOT``.

As with the INDEX, crate files are distributed into subdirectories based on the
first few characters of the crate's name.  By default, the prefixes are
lowercase (unless forced to mixed-case via ``romt crate --prefix=mixed``).  Romt
versions before 0.4.0 used mixed-case prefixes exclusively, as the author did
not know how to compute lowercase prefixes in nginx rules (this is now solved
using Perl with nginx).  Mixed-case prefixes caused problems when accessing a
crates mirror via both case-sensitive and case-insensitive shares
simultaneously, so lowercase prefixes are now preferred.

=========  =================  ==========
{prefix}   crate name length  crate name
=========  =================  ==========
1          1                  a
2          2                  ab
3/a        3                  abc
ab/cd      4 or more          abcd*
=========  =================  ==========

A crate with name ``{crate}`` and version ``{version}`` is found within
CRATES_ROOT at ``{prefix}/{crate}/{crate}-{version}.crate``.

For example, version 1.0.99 of the ``serde`` crate would be found by default at
``crates/se/rd/serde/serde-1.0.99.crate``.

Initializing
------------

The INDEX and CRATES_ROOT areas must be initialized before use.  The
initialization method depends on the use.

The ``romt crate init`` command creates the INDEX and CRATES_ROOT areas and
prepares the INDEX as a Git repository with remote named ``origin`` that points
to a Git remote given by INDEX_URL.  This is suitable for the laptop scenario
and for the Export machine in the disconnected network scenario.

The ``romt crate init-import`` command is for use on the Import machine in the
disconnected scenario.  It's similar to ``init``, but instead of configuring
INDEX's ``origin`` remote to INDEX_URL, it configures ``origin`` to be a local
bundle file at BUNDLE_PATH that conveys INDEX commits sent from the Export
machine.  Subsequent ``unpack`` commands will query the ``url`` key for the
``origin`` remote within INDEX to determine BUNDLE_PATH.  The default value of
BUNDLE_PATH is ``origin.bundle`` within the INDEX directory; this may be changed
via ``--bundle-path BUNDLE_PATH``.

By default, crate files are stored on-disk using lowercase prefixes.  Using
``romt crate --prefix=mixed`` forces the use of mixed-case prefixes (as used in
Romt before version 0.4.0).  Lowercase prefixes are recommended.  Romt will not
permit the use of ``--prefix=mixed`` when using case-insensitive filesystems
(such as on Windows) to avoid creating unpredictable-case prefixes due to case
aliasing issues.

Romt (as of version 0.4.0) creates a ``config.toml`` file in CRATES_ROOT as an
implementation detail to aid in the transition to lowercase crate prefixes;
users should generally not have to interact with it.  Future versions of Romt
may remove this configuration file and use lowercase prefixes exclusively.

config
------

After initialization via ``init`` or ``init-import``, the local INDEX repository
will be properly setup.  If the INDEX contents will be served to clients
directly (e.g., for the laptop scenario or the Import machine in the offline
network scenario), it must be configured for the URL of the offline server by
editing the file ``config.json`` within the top-level directory of INDEX.  The
default contents of ``config.json`` (as found on Github) are::

  {
    "dl": "https://crates.io/api/v1/crates",
    "api": "https://crates.io"
  }

The ``dl`` key in particular informs ``cargo`` and other INDEX consumers how to
download crate files cataloged by INDEX.

The ``romt crate config`` command edits ``config.json`` based on the value of
SERVER_URL; this defaults to ``http://localhost:8000`` (as used by ``romt
serve``, described later).  It may be changed via the option ``--server-url
SERVER_URL``.

Given SERVER_URL, the ``dl`` key will be set to::

  SERVER_URL/crates/{crate}/{crate}-{version}.crate

By default, this will be::

  http://localhost:8000/crates/{crate}/{crate}-{version}.crate

Rust tooling (e.g., Cargo) will start with the value of the ``dl`` key and
substitute ``{crate}`` with the name of the crate and ``{version}`` with the
crate's version number to form the URL for a given crate file.

Only the SERVER_URL portion of the ``dl`` key is currently configurable; the
rest of the URL is hard-coded to match the conventions of ``romt serve``.
However, any changes manually committed to ``config.json`` will be preserved by
subsequent Romt operations.

Changes to ``config.json`` are committed to the local ``working`` branch, and
ultimately published to the local ``master`` branch (via the ``mark`` command).
As upstream commits are merged into ``master``, Romt will ensure that the local
``config.json`` changes take precedence over possible upstream changes.

``mark``
--------

Romt uses a branch named ``mark`` as a commit placeholder within INDEX.  It
tracks progress through the INDEX, marking one operation's END commit for use as
the next operation's START commit.

The ``romt crate mark`` command sets both the ``mark`` branch and the ``master``
branch to the commit indicated by END.  START defaults to ``mark`` such that
subsequent operations pick up where previous ones left off.  END defaults to
``HEAD`` (generally the ``working`` branch) such that RANGE includes all
unprocessed commits.

Note that working copy modifications (merges and edits) are done on the
``working`` branch.  Changes won't be visible on the ``master`` branch until
after the ``mark`` command is executed, ensuring clients won't see partially
complete modifications while the repository is being updated.

Pulling INDEX commits
---------------------

Before downloading crate files, the INDEX must be updated.  The ``romt crate
pull`` command fetches the latest commits from INDEX's ``origin`` remote into
the ``remotes/origin/master`` branch, then marks this location in the local
branch ``origin_master`` for convenience of reference.  The fetched commits are
then merged into the HEAD branch (typically ``working``), preserving any local
modifications that may have been made to ``config.json``.  If the merge
operation fails, the working copy is reset to ``remotes/origin/master`` and any
local changes to ``config.json`` that may have been present in ``HEAD`` before
the pull are re-applied.

Note: In Romt version 0.1.3 and earlier, ``HEAD`` defaulted to ``master``,
leaving a small race window where partial modifications to the repository could
be visible to clients (e.g., ``master`` might include mention of a crate that
hasn't yet been downloaded).  Therefore, Romt now defaults to using the branch
``working`` for merging and other modifications to the repository.  These
changes won't be visible on ``master`` until the ``mark`` command is invoked.
At each ``pull`` operation, Romt will upgrade the repository to use a
``working`` branch if ``HEAD`` is not set to ``working`` and the ``working``
branch does not yet exist.  To avoid this, pre-create a ``working`` branch (with
arbitrary content) before executing a ``pull`` command, and Romt will not switch
``HEAD`` to ``working``.

Downloading
-----------

Downloading of crate files is requested via the ``romt crate download`` command.

The subset of crate files to download is determined by the RANGE of commits
(from START through END) in the INDEX.  Each file is downloaded from the
upstream location indicated by CRATES_URL as explained previously.  As part of
downloading, Romt verifies the SHA256 hash of each crate against the value
stored in INDEX to ensure file integrity.

Each crate file is stored below CRATES_ROOT using the prefix mechanism described
earlier.

Sometimes individual crate files are removed from the upstream mirror.  Romt
warns about such failures and continues with the rest of the crates in the
RANGE.  After attempting all crates in RANGE, by default Romt will abort if
any crates failed to download.  The option ``--keep-going`` allows Romt to
continue past download failures to subsequent steps (e.g., packing an archive
file).

Packing/unpacking
-----------------

The ``romt crate pack`` command creates a Git bundle file of the commits in
RANGE, then packs the bundle file along with the downloaded crate files included
in RANGE into an ``ARCHIVE`` file.

The archive file may be moved to another machine and unpacked using the
``unpack`` command.

For both ``pack`` and ``unpack``, the ``ARCHIVE`` file is named
``crates.tar.gz`` by default; this may be changed via the option ``--archive
ARCHIVE``.

For the ``pack`` command, a Git bundle file is written to disk at BUNDLE_PATH
before being inserted into the ARCHIVE.  The default value of BUNDLE_PATH is
``origin.bundle`` within the INDEX directory; this may be changed via
``--bundle-path BUNDLE_PATH``.

An ``unpack`` command extracts the Git bundle file and all crate files, placing
the bundle at the BUNDLE_PATH value specified with the ``init-import`` command.
Crate files are unpacked into CRATES_ROOT.  Note that crate files are not
verified automatically as part of the ``unpack`` operation.

An archive file uses the directory structure of CRATES_ROOT for crate files and
the default on-disk location for the Git, and it places the Git bundle file into
the archive with the hard-coded path ``git/crates.io-index/origin.bundle``.  For
example::

  git/crates.io-index/origin.bundle
  crates/3/n/num/num-0.0.1.crate
  crates/gl/ob/glob/glob-0.0.1.crate
  crates/se/mv/semver/semver-0.1.0.crate
  crates/uu/id/uuid/uuid-0.0.1.crate

Verify
------

The ``romt crate verify`` command checks the integrity of each downloaded crate
included in RANGE within INDEX.  Using the SHA256 hash values contained in INDEX
for each crate file, Romt ensures that the downloaded crate files have not been
corrupted and that no files in RANGE are missing.

``update``, ``export``, and ``import``
--------------------------------------

For each of the three main use cases, there is short command name that implies
the needed steps:

- ``update`` is the same as ``pull download mark``.  This is useful for the
  laptop scenario.

- ``export`` is the same as ``pull download pack mark``.  This is useful for the
  Export machine in the disconnected network scenario.

- ``import`` is the same as ``unpack pull verify mark``.  This is useful for the
  Import machine in the disconnected network scenario.

Listing downloaded crate files
------------------------------

The ``romt crate list`` command prints the filename for each crate
included in RANGE within INDEX, independent of whether those crate files have
been downloaded.

For example, to see what new crates are available, first ``pull`` the latest
INDEX and then ``list``:

.. code-block:: sh

  romt crate pull list

With example output::

  pull...
  list...
  gc-0.3.4.crate
  brs-0.2.0.crate
  cxx-0.3.1.crate
  irc-0.14.0.crate
  scd-0.1.3.crate
  [...]

``crate`` scenarios
--------------------

For the laptop scenario, only the ``update`` command is needed, after which
crates will be available for serving via ``romt serve`` (or other means).  For
example, to download the latest crates:

.. code-block:: sh

    romt crate update

For the disconnected network scenario, crate versions are downloaded and packed
on an Internet-connected Export machine, then unpacked on an Import machine,
e.g.:

- On the Export machine:

  - First, download the latest crates and pack them into ``crates.tar.gz``:

    .. code-block:: sh

      romt crate export

  - Transfer the resulting ``crates.tar.gz`` file onto the Import machine.

- On the Import machine:

  - Unpack the archive:

    .. code-block:: sh

      romt crate import

``serve`` operation
===================

The ``serve`` operation runs a local HTTP server exposing toolchain, rustup, and
crate artifacts.

``serve`` URL
-------------

By default, ``romt serve`` listens at the following URL::

  http://localhost:8000

To use ``http://ADDR:PORT``, use the switches ``--bind ADDR`` and/or ``--port
PORT``.

``serve`` directory layout
--------------------------

``romt serve`` expects the current working directory (``$PWD``) to contain all
artifacts being served.  Artifacts must be laid out in their default locations
described elsewhere, as follows::

    $PWD/
      dist/
      rustup/
      crates/
      git/
        crates.io-index/

URLs of the form ``http://ADDR:PORT/{path}`` generally map directly to
``$PWD/{path}``; exceptions are noted below.

URLs with paths below ``/crates/`` are expected to be of the following form::

  http://ADDR:PORT/crates/{crate}/{crate}-{version}.crate

``romt serve`` will rewrite the URL to insert the expected ``{prefix}`` used in
CRATES_ROOT, effectively transforming the URLs to::

  http://ADDR:PORT/crates/{prefix}/{crate}/{crate}-{version}.crate

URLs with paths below ``/git/`` refer to Git repositories.  Romt uses
``git-http-backend`` as distributed with Git to serve these repositories.
For this purpose, ``romt serve`` uses a ``cgi-bin/`` directory in the current
working directory to interface via CGI with ``git-http-backend``.

Upon launching ``romt serve``, Romt searches for one of the following files in
``cgi-bin/`` (depending on the platform):

  - On Windows::

      git-http-backend.bat
      git-http-backend.exe

  - On non-Windows::

      git-http-backend.sh
      git-http-backend

If found, Romt will use that file for serving Git repositories via CGI.  If not
found, Romt will look in known locations for the ``git-http-backend`` executable
and create a platform-dependent wrapper script in ``cgi-bin/`` to invoke the
executable; the script is named ``git-http-backend.bat`` on Windows and
``git-http-backend.sh`` on non-Windows.

Currently, Romt probes for the backend in these hard-coded locations (depending
on the platform):

- On Windows:

  - ``C:/Program Files/Git/mingw64/libexec/git-core/git-http-backend.exe``

- On non-Windows:

  - ``/usr/lib/git-core/git-http-backend`` (typical Linux)
  - ``/usr/libexec/git-core/git-http-backend`` (Alpine Linux)

To manually setup the Git backend, create a script file in ``cgi-bin/`` with
contents similar to these examples (depending on platform):

- On Windows, create ``cgi-bin/git-http-backend.bat`` with contents::

    @echo off
    "C:\Program Files\Git\mingw64\libexec\git-core\git-http-backend.exe"

- On non-Windows, create ``cgi-bin/git-http-backend.sh`` with contents::

    #!/bin/sh
    exec '/usr/lib/git-core/git-http-backend'

  Then make the script executable:

  .. code-block:: sh

    chmod +x cgi-bin/git-http-backend.sh

nginx configuration
===================

Rust artifacts may optionally be served via the nginx web server.  A simple
example for Ubuntu Linux is shown below.  If you change host or port values
below, configure the index repository via:
.. code-block:: sh

  romt crate config --server-url <SERVER_URL>

Below is a sample nginx configuration.

Place the following content into ``/etc/nginx/sites-available/rust``.  Make
adjustments as indicated by each ``TODO``.  These instructions assume crates
are stored using lowercase prefixes; if using mixed-case prefixes, adjust as
directed by the ``TODO`` comments::

  server {
    listen 8000 default_server;
    listen [::]:8000 default_server;

    # TODO: Change to absolute path to mirror directory:
    root /ABSOLUTE/PATH/TO/mirror;

    server_name _;

    location / {
      autoindex on;
    }

    # Support serving of Git repositories via git-http-backend.
    location ~ /git(/.*) {

      # TODO: Change to absolute path to mirror/git directory:
      fastcgi_param GIT_PROJECT_ROOT    /ABSOLUTE/PATH/TO/mirror/git;

      include       fastcgi_params;
      fastcgi_pass  unix:/var/run/fcgiwrap.socket;
      fastcgi_param SCRIPT_FILENAME     /usr/lib/git-core/git-http-backend;
      fastcgi_param GIT_HTTP_EXPORT_ALL "";
      fastcgi_param PATH_INFO           $1;
    }

    # Rewrite URLs like /crates/{crate}/{crate}-{version}.crate to use
    # a prefix based on the crate name.  Special cases for crate names
    # with 1, 2, 3, and 4-or-more characters:
    #   a/a-{version}.crate         -> 1/a/a-{version}.crate
    #   ab/ab-{version}.crate       -> 2/aa/ab-{version}.crate
    #   abc/abc-{version}.crate     -> 3/a/abc/abc-{version}.crate
    #   abcd*/abcd*-{version}.crate -> ab/cd/abcd*-{version}.crate

    # TODO: Comment out this line for mixed-case crate prefixes:
    rewrite "^/crates/.*$" "$crates_uri"  last;

    # TODO: Uncomment these four lines for mixed-case crate prefixes:
    # rewrite "^/crates/([^/])/([^/]+)$"                     "/crates/1/$1/$2"  last;
    # rewrite "^/crates/([^/]{2})/([^/]+)$"                  "/crates/2/$1/$2"  last;
    # rewrite "^/crates/([^/])([^/]{2})/([^/]+)$"            "/crates/3/$1/$1$2/$3"  last;
    # rewrite "^/crates/([^/]{2})([^/]{2})([^/]*)/([^/]+)$"  "/crates/$1/$2/$1$2$3/$4" last;

  }

Serving crates with lowercase prefixes requires Perl support in nginx (on
Ubuntu, this requires the package ``nginx-extras`` instead of ``nginx-full``);
Perl support is not required for mixed-case prefixes.  To serve crates with
lowercase prefixes, create the file ``/etc/nginx/conf.d/perl.conf`` with the
below contents::

  # Reference: https://nginx.org/en/docs/http/ngx_http_perl_module.html
  # Include the perl module
  perl_modules perl/lib;

  # The variable `$crates_uri` will be computed by the Perl subroutine
  # below, adding a lowercase prefix as required based on the crate name.

  perl_set $crates_uri 'sub {
      my $r = shift;
      my $uri = $r->uri;
      # Remove all newline characters to avoid CRLF injection vulnerability
      # (https://stackoverflow.com/questions/3666003/how-i-can-translate-uppercase-to-lowercase-letters-in-a-rewrite-rule-in-nginx-we/68054489#68054489):
      $uri =~ s/\R//g;

      if ($uri =~ m@^/crates/([^/])/([^/]+)$@) {
          $uri = "/crates/1/" . "$1/$2";
      } elsif ($uri =~ m@^/crates/([^/]{2})/([^/]+)$@) {
          $uri = "/crates/2/" . "$1/$2";
      } elsif ($uri =~ m@^/crates/([^/])([^/]{2})/([^/]+)$@) {
          $uri = lc("/crates/3/$1/") . "$1$2/$3";
      } elsif ($uri =~ m@^/crates/([^/]{2})([^/]{2})([^/]*)/([^/]+)$@) {
          $uri = lc("/crates/$1/$2/") . "$1$2$3/$4";
      }
      return $uri;
  }';

Activate the ``rust`` site via::

  ln -s /etc/nginx/sites-available/rust /etc/nginx/sites-enabled/

Amazon S3 storage
=================

Currently static artifacts hosted on Rust CDNs are served via Amazon S3 buckets.
At times directly accessing the bucket can be helpful.

A helpful command-line tool for use with S3 buckets is ``awscli``:
https://github.com/aws/aws-cli

Rust https URLs map to S3 bucket URLs as follows:

- https://static.rust-lang.org -> s3://static-rust-lang-org
- https://static.crates.io -> s3://crates-io

Note: unfortunately, the "list" privilege is disabled for the ``crates-io``
bucket.

Here are some common operations on S3 buckets:

- List files beginning with PREFIX:

  .. code-block:: sh

    aws s3 ls --no-sign-request s3://BUCKET_NAME/PREFIX

  Add ``--recursive`` flag to recurse into subdirectories.

- Download a file:

  .. code-block:: sh

    aws s3 cp --no-sign-request s3://BUCKET_NAME/path/file local_file

Examples:

- List channel files for toolchain for 2020-04-30:

  .. code-block:: sh

    aws s3 ls --no-sign-request s3://static-rust-lang-org/dist/2020-04-30/chan

  with example output::

    2020-04-29 20:23:44         10 channel-rust-nightly-date.txt
    2020-04-29 20:23:44        833 channel-rust-nightly-date.txt.asc
    2020-04-29 20:23:44         96 channel-rust-nightly-date.txt.sha256
    2020-04-29 20:23:44         40 channel-rust-nightly-git-commit-hash.txt
    ...

- List ``rustup`` versions:

  .. code-block:: sh

    aws s3 ls --no-sign-request s3://static-rust-lang-org/rustup/archive/

  with example output::

                           PRE 0.2.0/
                           PRE 0.3.0/
                           PRE 0.4.0/
                           ...

- Download ``serde-1.0.99.crate``:

  .. code-block:: sh

    aws s3 cp --no-sign-request s3://crates-io/crates/serde/serde-1.0.99.crate .

  This is functionally equivalent to:

  .. code-block:: sh

    curl -O https://static.crates.io/crates/serde/serde-1.0.99.crate

Troubleshooting
===============

Proxy server troubleshooting
----------------------------

The author has not tested Romt with a proxy server, but user feedback indicates
it's possible (see https://github.com/drmikehenry/romt/issues/10).  The
``httpx`` library's support for proxying is documented at:
https://www.python-httpx.org/advanced/#http-proxying

``httpx`` understands several environment variables (documented at the page
above) that may be used to influence proxy operation.  In addition, ``httpx``
has information about debugging proxy-related issues at:
https://www.python-httpx.org/contributing/#development-proxy-setup

Also, ``httpx`` can produce more debugging information by setting the
environment variable ``HTTPX_LOG_LEVEL`` to ``trace`` (as documented at
https://www.python-httpx.org/environment_variables/).  As a sample invocation on
Linux::

  HTTPX_LOG_LEVEL=trace romt toolchain -v -s nightly -t all fetch-manifest

Download timeouts
-----------------

Romt 0.3.0 added support for simultaneous downloading based on the ``httpx``
library; this came with a a default timeout of five seconds which can lead to
``ConnectTimeout`` or ``ReadTimeout`` errors depending on choice of
``--num-jobs`` and network characteristics (see
https://github.com/drmikehenry/romt/issues/16).

Romt 0.4.0 adds a ``--timeout`` switch to control this timeout, and changed the
default value to sixty seconds.  If timeouts are still occurring, use a larger
timeout value (or use ``--timeout 0`` to disable timeouts altogether).

Reference
=========

- "Downloading all the crates on crates.io" provides good reference information
  on mirroring Rust artifacts:
  https://www.pietroalbini.org/blog/downloading-crates-io/

- More information on Rust checksumming, signatures, etc., can be found at:
  https://internals.rust-lang.org/t/future-updates-to-the-rustup-distribution-format/4196

- Information on the "rustup" project:
  https://github.com/rust-lang/rustup
