*******
History
*******

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
