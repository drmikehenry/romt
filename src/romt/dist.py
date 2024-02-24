import argparse
import urllib.parse
from pathlib import Path
from typing import List, Optional

from romt import base, common, error


def expand_target_alias(target: str) -> str:
    if target == "linux":
        target = "x86_64-unknown-linux-gnu"
    elif target == "windows":
        target = "x86_64-pc-windows-msvc"
    elif target == "darwin":
        target = "x86_64-apple-darwin"
    return target


def target_exe_suffix(target: str) -> str:
    parts = target.split("-")
    if "windows" in parts:
        suffix = ".exe"
    else:
        suffix = ""
    return suffix


def append_exe_suffix(s: str, target: str) -> str:
    suffix = target_exe_suffix(target)
    return s + suffix


def path_append_exe_suffix(path: Path, target: str) -> Path:
    suffix = target_exe_suffix(target)
    return common.path_append(path, suffix)


def require_specs(specs: List[str]) -> List[str]:
    if not specs:
        raise error.UsageError("missing required SPEC; try --select")
    return specs


def require_targets(
    targets: List[str], *, default: Optional[str] = None
) -> List[str]:
    if not targets:
        if default is None:
            raise error.UsageError("missing required TARGET; try --target")
        targets = [default]
    return targets


class DistMain(base.BaseMain):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args)
        self._specs: Optional[List[str]] = None
        self._targets: Optional[List[str]] = None

    @property
    def specs(self) -> List[str]:
        if self._specs is None:
            specs = common.split_flatten_words(self.args.specs)
            self._specs = specs
        return self._specs

    @specs.setter
    def specs(self, value: List[str]) -> None:
        self._specs = list(value)

    @property
    def targets(self) -> List[str]:
        if self._targets is None:
            patterns = [
                expand_target_alias(pattern)
                for pattern in common.normalize_patterns(self.args.targets)
            ]
            self._targets = patterns
        return self._targets

    @targets.setter
    def targets(self, targets: List[str]) -> None:
        self._targets = list(targets)

    @property
    def dest_path(self) -> Path:
        return Path(self.args.dest)

    def dest_path_from_rel_path(self, rel_path: str) -> Path:
        return self.dest_path / rel_path

    def url_from_rel_path(self, rel_path: str) -> str:
        base_url = self.args.url
        if not base_url.endswith("/"):
            base_url += "/"
        return str(urllib.parse.urljoin(base_url, rel_path))
