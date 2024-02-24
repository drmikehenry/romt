import argparse
import http.server
import os
from pathlib import Path
from typing import Optional

import romt.crate
from romt import common

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
    if common.is_windows:
        candidates = [
            "git-http-backend.exe",
            "git-http-backend.bat",
        ]
    else:
        candidates = [
            "git-http-backend.sh",
            "git-http-backend",
        ]
    for git_cgi_name in candidates:
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

    def _crates_config(self) -> romt.crate.CratesConfig:
        crates_config = getattr(self, "_cached_crates_config", None)
        if crates_config is None:
            crates_config = romt.crate._read_crates_config(Path("crates"))
            self._cached_crates_config = crates_config
        return crates_config

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
            prefix_style = romt.crate._crates_config_prefix_style(
                self._crates_config()
            )
            parent = os.path.dirname(path)
            name = os.path.basename(parent)
            prefix = romt.crate.crate_prefix_from_name(name, prefix_style)
            path = "/crates/{}/{}/{}".format(
                prefix,
                name,
                os.path.basename(path),
            )

        if self.path != path:
            common.iprint(f"Rewrite URL: {self.path} -> {path}")
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

if common.is_windows:
    GIT_HTTP_BACKEND_SOURCES = [
        "C:/Program Files/Git/mingw64/libexec/git-core/git-http-backend.exe",
    ]
else:
    GIT_HTTP_BACKEND_SOURCES = [
        "/usr/lib/git-core/git-http-backend",
        # Alpine Linux:
        "/usr/libexec/git-core/git-http-backend",
    ]


def get_git_http_backend_path() -> Optional[Path]:
    for source in GIT_HTTP_BACKEND_SOURCES:
        source_path = Path(source)
        if source_path.is_file():
            return source_path
    return None


def make_git_cgi_script(git_http_backend_path: Path) -> None:
    cgi_path = Path("cgi-bin")
    if not cgi_path.is_dir():
        common.iprint(f"mkdir {cgi_path}")
        cgi_path.mkdir()
    if common.is_windows:
        extension = ".bat"
        template = '@echo off\n"{}"\n'
    else:
        extension = ".sh"
        template = "#!/bin/sh\nexec '{}'\n"
    script_path = cgi_path / ("git-http-backend" + extension)
    script = template.format(git_http_backend_path)
    common.iprint(f"Create script {script_path} ({repr(script)})")
    script_path.write_text(script, encoding="utf-8")
    if not common.is_windows:
        common.chmod_executable(script_path)


def setup_git_cgi() -> None:
    os.environ["GIT_HTTP_EXPORT_ALL"] = ""
    os.environ["GIT_PROJECT_ROOT"] = os.path.abspath("git")

    git_cgi_path = find_git_cgi_path()
    if git_cgi_path:
        if not common.is_windows and not common.is_executable(git_cgi_path):
            common.eprint(
                f"Warning: setting executable flag on {git_cgi_path}"
            )
            common.chmod_executable(git_cgi_path)
    else:
        git_http_backend_path = get_git_http_backend_path()
        if git_http_backend_path:
            make_git_cgi_script(git_http_backend_path)
        else:
            common.eprint("Warning: missing git-http-backend; no Git support")


class Main:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args

    def run(self) -> None:
        common.iprint("server running")
        setup_git_cgi()

        # Avoid type hint warning about missing http.server.test by
        # using getattr() to fetch the function.
        serve_func = getattr(http.server, "test")

        serve_func(
            HandlerClass=Handler, bind=self.args.bind, port=self.args.port
        )
