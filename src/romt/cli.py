#!/usr/bin/env python3
# coding=utf-8

import argparse
import sys

from romt import common
from romt import error
import romt.crate
import romt.rustup
import romt.serve
import romt.toolchain

__version__ = "0.3.3"

project_name = "romt"

description = """\
Rust Offline Mirror Tool
"""

epilog = """\
See ``{project_name} --readme`` for more details.
""".format(
    project_name=project_name
)


def readme_from_pkg_resources() -> str:
    # This method works when the package is properly installed via "pip".
    import pkg_resources
    import email
    import textwrap

    try:
        dist = pkg_resources.get_distribution(project_name)
        meta = dist.get_metadata(dist.PKG_INFO)
    except (pkg_resources.DistributionNotFound, FileNotFoundError):
        return ""
    msg = email.message_from_string(meta)
    desc = msg.get("Description", "").strip()
    if not desc and not msg.is_multipart():
        desc = msg.get_payload().strip()
    if "\n" in desc:
        first, rest = desc.split("\n", 1)
        desc = "\n".join([first, textwrap.dedent(rest)])
    return desc


def readme_from_file() -> str:
    # This method works with PyInstaller.
    import pkgutil

    text = ""
    try:
        readme = pkgutil.get_data(project_name, "README.rst")
        if readme is not None:
            text = readme.decode("utf-8")
    except FileNotFoundError:
        text = ""
    return text


def readme() -> None:
    desc = readme_from_pkg_resources()
    if not desc:
        desc = readme_from_file()
    if not desc:
        desc = "README.rst is not available."
    common.iprint(desc)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )

    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="verbose output",
    )

    parser.add_argument(
        "-q", "--quiet", action="count", default=0, help="quiet output",
    )

    parser.add_argument(
        "--readme", action="store_true", help="display README.rst",
    )

    parser.add_argument(
        "--num-jobs",
        "-j",
        type=int,
        default=4,
        action="store",
        help="number of simultaneous download jobs (default %(default)s)",
    )


def make_parser() -> argparse.ArgumentParser:
    common_parser = argparse.ArgumentParser(add_help=False)
    add_common_arguments(common_parser)

    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(dest="subparser_name", help="OPERATION")

    crate_parser = subparsers.add_parser(
        "crate",
        help=romt.crate.description,
        description=romt.crate.description,
        epilog=romt.crate.epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
    )

    romt.crate.add_arguments(crate_parser)

    rustup_parser = subparsers.add_parser(
        "rustup",
        help=romt.rustup.description,
        description=romt.rustup.description,
        epilog=romt.rustup.epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
    )

    romt.rustup.add_arguments(rustup_parser)

    toolchain_parser = subparsers.add_parser(
        "toolchain",
        help=romt.toolchain.description,
        description=romt.toolchain.description,
        epilog=romt.toolchain.epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
    )

    romt.toolchain.add_arguments(toolchain_parser)

    serve_parser = subparsers.add_parser(
        "serve",
        help=romt.serve.description,
        description=romt.serve.description,
        epilog=romt.serve.epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
    )

    romt.serve.add_arguments(serve_parser)

    return parser


def main() -> None:
    parser = make_parser()
    args = parser.parse_args()
    common.set_max_verbosity(common.VERBOSITY_INFO + args.verbose - args.quiet)

    try:
        cmd = args.subparser_name
        if args.readme:
            readme()
        elif cmd is None:
            raise error.UsageError("missing OPERATION (try --help)")
        elif cmd == "crate":
            romt.crate.Main(args).run()
        elif cmd == "rustup":
            romt.rustup.Main(args).run()
        elif cmd == "toolchain":
            romt.toolchain.Main(args).run()
        elif cmd == "serve":
            romt.serve.Main(args).run()

    except error.Error as e:
        common.eprint(e)
        sys.exit(1)

    except KeyboardInterrupt:
        common.eprint("Keyboard interrupt")


if __name__ == "__main__":
    main()
