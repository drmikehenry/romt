import argparse
import importlib.metadata
import sys
from typing import List, Optional

import romt.crate
import romt.rustup
import romt.serve
import romt.toolchain
from romt import common, error

project_name = "romt"

description = """\
Rust Offline Mirror Tool
"""

epilog = """\
See ``{project_name} --readme`` for more details.
""".format(project_name=project_name)


# For Python 3.10+.
# This fails on Python 3.8 and 3.9 for `poetry install` and `pip install`.
# It works, however, for PyInstaller builds for Python 3.8+.
def readme_from_importlib() -> str:
    meta = importlib.metadata.metadata("romt")
    text = meta["Description"] or ""
    return text.strip()


# Required on Python 3.8 and 3.9 for `poetry install`, `pip install`.
def readme_from_pkg_resources() -> str:
    import email
    import textwrap

    try:
        # `pkg_resources` comes from `setuptools` which might not be installed.
        # It is also deprecated. so we squelch warnings during import.
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import pkg_resources
    except ImportError:
        return ""

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


def readme() -> None:
    desc = readme_from_importlib()
    if not desc:
        desc = readme_from_pkg_resources()
    if not desc:
        desc = "README.rst is not available."
    common.iprint(desc)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="verbose output",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="count",
        default=0,
        help="quiet output",
    )

    parser.add_argument(
        "--num-jobs",
        "-j",
        type=int,
        default=4,
        action="store",
        help="number of simultaneous download jobs (default %(default)s)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        dest="timeout_seconds",
        default=60,
        action="store",
        help="download timeout seconds (default %(default)s; 0 => no timeout)",
    )


def make_parser() -> argparse.ArgumentParser:
    romt_version = importlib.metadata.version("romt")

    common_parser = argparse.ArgumentParser(add_help=False)
    add_common_arguments(common_parser)

    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version", action="version", version="%(prog)s " + romt_version
    )

    parser.add_argument(
        "--readme",
        action="store_true",
        help="display README.rst",
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


def run(sys_args: Optional[List[str]] = None) -> int:
    parser = make_parser()
    args = parser.parse_args(args=sys_args)
    if args.readme:
        readme()
        return 0
    cmd = args.subparser_name
    try:
        if cmd is None:
            raise error.UsageError("missing OPERATION (try --help)")

        common.set_max_verbosity(
            common.VERBOSITY_INFO + args.verbose - args.quiet
        )

        if cmd == "crate":
            romt.crate.Main(args).run()
        elif cmd == "rustup":
            romt.rustup.Main(args).run()
        elif cmd == "toolchain":
            romt.toolchain.Main(args).run()
        elif cmd == "serve":
            romt.serve.Main(args).run()

    except error.Error as e:
        common.eprint(e)
        return 1

    except KeyboardInterrupt:
        common.eprint("Keyboard interrupt")

    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
