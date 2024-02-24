import argparse
from pathlib import Path
from typing import List, Optional

import romt.download
from romt import error


def verify_commands(commands: List[str], valid_commands: List[str]) -> None:
    for command in commands:
        if command not in valid_commands:
            raise error.UsageError(f"invalid COMMAND {repr(command)}")


def add_downloader_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--assume-ok",
        action="store_true",
        default=False,
        help="assume already-downloaded files are OK (skip hash check)",
    )


class BaseMain:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self._downloader: Optional[romt.download.Downloader] = None

    @property
    def downloader(self) -> romt.download.Downloader:
        if self._downloader is None:
            num_jobs = max(self.args.num_jobs, 1)
            timeout_seconds = max(self.args.timeout_seconds, 0)
            self._downloader = romt.download.Downloader(
                num_jobs=num_jobs, timeout_seconds=timeout_seconds
            )
        return self._downloader

    def get_archive_path(self) -> Path:
        if not self.args.archive:
            raise error.UsageError("missing archive name")
        return Path(self.args.archive)

    def _run(self) -> None:
        # Override in derived classes.
        pass

    def run(self) -> None:
        try:
            self._run()
        finally:
            if self._downloader is not None:
                self._downloader.close()
                self._downloader = None
