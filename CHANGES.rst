*******
History
*******

Version 0.3.4
=============

- Fix detection of toolchain targets in the presence of artifacts shared across
  targets.  Previously, a given target was detected whenever any one of that
  target's artifact files was found to be present.  This algorithm is
  insufficient when an artifact file may be shared across different targets.
  Instead, a target is now detected with either *all* artifacts for that target
  are present, or when at least one of the target's artifacts is present and is
  unique to that target (not shared with other targets).  The incorrect target
  detection could lead to ``MissingFileError`` exceptions when unpacking a
  toolchain archive whenever targets not present in the archive share artifact
  files with targets present in the archive.

- Update list of known targets for ``rustup``.

Version 0.3.3
=============

- Fix issue #13 regarding duplicate toolchain artifact URLs.  Some distinct
  toolchain artifacts may share the same download URL (e.g.,
  ``.../rust-docs-nightly-x86_64-unknown-linux-gnu.tar.xz`` is shared across
  several other processor variants).  Before version 0.3.0, this was handled
  naturally by the sequential nature of the download operation, but the new
  asynchronous support from 0.3.0 failed to account for the possible
  duplication.

Version 0.3.2
=============

- Fix issue #12 causing the below error with ``romt crate import`` on Windows::

    INDEX remote ``origin`` must have ``url`` as a local file

  Romt requires the URL to be a local path (e.g., ``/path/to/origin.bundle``)
  instead of a URL with a schema (e.g., ``https://server/path``).  The check for
  URL schemas was overzealous.  URLs with a leading ``schema:`` prefix should be
  rejected, but Windows paths with drive letters such as
  ``c:/path/to/origin.bundle`` are local; the ``c:`` drive letter should not be
  considered to be a ``schema:`` prefix.  Single-character schema-like prefixes
  are no longer treated as errors.

- Clarify quick-start instructions, pointing out steps which are one-time only.

- Add probe for Alpine Linux's default location for ``git-http-backend``
  (``/usr/libexec/git-core/git-http-backend``) in addition to the more common
  location (``/usr/lib/git-core/git-http-backend``).  This eliminates the need
  for manual configuration with Alpine (see issue #11).

- Improve exception messages.  For `DownloadError` in particular, embed the
  `repr()` of the associated exception from `httpx` to aid in debugging
  `httpx`-related errors (see also issue #10 for more debugging of `httpx`
  proxy-related issues).

Version 0.3.1
=============

- Fix ``romt crate --keep-going`` to correctly handle ``403 Forbidden`` and
  other HTTP status failures (thanks to Anthony Gray,
  https://github.com/f34rt3hbunn3h).

  When porting from `requests` to `httpx`, the exception handling in the
  `Downloader` class was incorrectly switched from the ``requests`` library's
  ``RequestException`` base class to the ``httpx`` library's ``RequestError``
  class; the former is the base class for all of the exceptions in ``requests``,
  whereas the latter doesn't cover all exceptions in ``httpx``.  This fix
  switches the exception handler to properly use ``httpx.HTTPError`` to catch
  all `httpx` library exceptions.

  References:
  - https://docs.python-requests.org/en/master/_modules/requests/exceptions/
  - https://www.python-httpx.org/exceptions/

Version 0.3.0
=============

- Add support for multiple simultaneous download jobs via ``--num-jobs``,
  enabled by switching from the ``requests`` package to ``httpx``.

- Drop support for Python 3.5, as ``httpx`` requires at least Python 3.6.

Version 0.2.2
=============

- Fix support for Python 3.5, converting several instances of ``pathlib.Path``
  to ``str`` for use with functions like ``open()``.

Version 0.2.1
=============

- ``romt crate config`` now implies ``romt crate mark``, fixing a regression in
  Romt 0.2.0.  In older versions, only a single ``master`` branch was used for
  the crates.io-index repository, so configuration changes were active
  immediately after ``romt crate config``.  As of Romt 0.2.0, such configuration
  changes are instead made in a ``working`` branch that's not visible to Cargo
  until the changes are published to ``master`` via a subsequent ``cargo crate
  mark`` operation.  To avoid the need to manually invoke ``cargo crate mark``,
  ``cargo crate config`` now performs the ``mark`` operation automatically.

Version 0.2.0
=============

- Switch to using a ``working`` branch as ``HEAD`` for the INDEX
  (crates.io-index) repository.  This ensures that partial modifications to
  INDEX aren't made available to clients on the ``master`` branch; these changes
  will be published atomically to ``master`` via the ``mark`` command.  Romt
  will automatically and transparently attempt to upgrade INDEX to use a
  ``working`` branch as part of the ``pull`` command.  See the description of
  the ``pull`` command in README.rst for more details.  As part of this work:

  - The ``--end`` switch now defaults to ``HEAD`` instead of ``master``, such
    that END uses the currently checked out branch (typically this
    will now be the ``working`` branch).

  - In addition to setting the ``mark`` branch, the ``mark`` command now also
    sets the ``master`` branch.

Version 0.1.3
=============

- Fix failure with ``romt serve`` when using the PyInstaller-built executable
  (see https://github.com/drmikehenry/romt/issues/1).  The implementation of
  ``romt serve`` is based on Python's ``http.serve`` module, which supports the
  use of CGI scripts in the local ``cgi-bin/`` directory.  In addition to
  standard executables, ``http.serve`` also supports the use of simple Python
  scripts in ``cgi-bin/``.  This is accomplished by invoking the current Python
  interpreter (recorded in ``sys.executable``) against the script file.
  Unfortunately, PyInstaller doesn't expose the Python interpreter via
  ``sys.executable``; instead, PyInstaller sets this variable to be the path of
  the generated executable.

  To avoid the above problem, Romt no longer supports the use of simple ``*.py``
  CGI scripts.  Instead, only the following CGI executables are usable
  (depending on platform):

  - On Windows::

      cgi-bin\git-http-backend.bat
      cgi-bin\git-http-backend.exe

  - On non-Windows::

      cgi-bin/git-http-backend.sh
      cgi-bin/git-http-backend

  If these aren't found at startup, Romt will generate a platform-dependent
  CGI script to invoke Git's HTTP backend.  See README.rst for more details.

Version 0.1.2
=============

- Add support for single-file executables using PyInstaller.

Version 0.1.1
=============

- Adjusted ``description`` in setup.py to avoid newlines.  Apparently multi-line
  descriptions throw off parsing of ``long_description``, leading to the below
  error with ``twine check dist/*``::

    `long_description` has syntax errors in markup and would
      not be rendered on PyPI.
    line 9: Error: Unexpected indentation.

Version 0.1.0
=============

- Initial version.
