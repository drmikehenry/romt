#!/usr/bin/env python3
# coding=utf-8

import argparse
import http.server
import os
from pathlib import Path
from typing import Optional

from romt import common
from romt.crate import crate_prefix_from_name


description = """\
Serve Rust artifacts via http.
"""

epilog = """\
Run a simple HTTP server providing access to mirrored toolchains, rustup, and
crates.  Includes use of git-http-backend to serve the crates index repository.
"""


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--port",
        type=int,
        action="store",
        default=8000,
        help="""server listen PORT (default: %(default)s)""",
    )

    parser.add_argument(
        "--bind",
        action="store",
        metavar="ADDR",
        default="localhost",
        help="""change bind ADDR (default: %(default)s)""",
    )


def find_git_cgi_path() -> Optional[Path]:
    cgi_path = Path("cgi-bin")
    for git_cgi_name in [
        "git-http-backend",
        "git-http-backend.exe",
        "git-http-backend.py",
    ]:
        git_path = cgi_path / git_cgi_name
        if git_path.is_file():
            return git_path
    return None


class Handler(http.server.CGIHTTPRequestHandler):
    # Avoid the use of fork on POSIX systems by disabling ``have_fork``.
    # This work-around is required as explained here:
    # https://stackoverflow.com/questions/47758247/ \
    #   local-embedded-http-server-that-can-respond-to-git-commands
    #
    # """
    #   The smart HTTP protocol of git is implemented in git-http-backend. This
    #   is a CGI binary that can be used in combination with some web-servers.
    #   Unfortunately it ignores the content-length of the request and relies
    #   on the server to close its input, which makes it incompatible with some
    #   CGI servers.
    #   ...
    #   [setting ``have_fork`` to False] causes the implementation to use
    #   subprocesses and pipes instead of fork to run the CGI binary. With this
    #   method, the incoming requests are buffered and written to a pipe, which
    #   is then closed. This fits the expected model of git-http-backend and
    #   therefore makes it work.
    # """
    have_fork = False

    def _rewrite_path(self) -> None:
        path = self.path
        if path.startswith("/git/"):
            git_cgi_path = find_git_cgi_path()
            if git_cgi_path is not None:
                path = path.replace("git", git_cgi_path.as_posix(), 1)
        elif path.startswith("/crates/"):
            # /crates/.../<name>/<name>-<version>.crate
            # ->
            # /crates/<prefix>/<name>/<name>-<version>.crate
            parent = os.path.dirname(path)
            name = os.path.basename(parent)
            rel_path = "crates/{}/{}/{}".format(
                crate_prefix_from_name(name), name, os.path.basename(path),
            )
            if os.path.isfile(rel_path):
                path = "/" + rel_path

        if self.path != path:
            common.iprint("Rewrite URL: {} -> {}".format(self.path, path))
            self.path = path

    def do_get(self) -> None:
        self._rewrite_path()
        super().do_GET()

    def do_head(self) -> None:
        self._rewrite_path()
        super().do_HEAD()

    def do_post(self) -> None:
        self._rewrite_path()
        super().do_POST()


# Work-around for non-compliant do_ALLCAPS functions.
setattr(Handler, "do_GET", Handler.do_get)
setattr(Handler, "do_HEAD", Handler.do_head)
setattr(Handler, "do_POST", Handler.do_post)

GIT_HTTP_BACKEND_SOURCES = [
    "/usr/lib/git-core/git-http-backend",
    "C:/Program Files/Git/mingw64/libexec/git-core/git-http-backend.exe",
]


class Main:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args

    def run(self) -> None:
        common.iprint("server running")
        os.environ["GIT_HTTP_EXPORT_ALL"] = ""
        os.environ["GIT_PROJECT_ROOT"] = os.path.abspath("git")

        git_cgi_path = find_git_cgi_path()
        if git_cgi_path is None:
            for source in GIT_HTTP_BACKEND_SOURCES:
                source_path = Path(source)
                if source_path.is_file():
                    cgi_path = Path("cgi-bin")
                    if not cgi_path.is_dir():
                        common.iprint("mkdir {}".format(cgi_path))
                        cgi_path.mkdir()
                    script = "import subprocess; subprocess.call({})".format(
                        repr(str(source_path))
                    )
                    script_path = cgi_path / "git-http-backend.py"
                    common.iprint(
                        "Create script {} ({})".format(
                            script_path, repr(script)
                        )
                    )
                    script_path.write_text(script, encoding="utf-8")
                    break
            else:
                common.eprint(
                    "Warning: could not setup cgi-bin/git-http-backend"
                )

        # Avoid type hint warning about missing http.server.test by
        # using getattr() to fetch the function.
        serve_func = getattr(http.server, "test")

        serve_func(
            HandlerClass=Handler, bind=self.args.bind, port=self.args.port
        )
