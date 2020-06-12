#!/usr/bin/env python3
# coding=utf-8

import copy
from pathlib import Path
from typing import (
    Any,
    Generator,
    Iterable,
    List,
    MutableMapping,
    Optional,
)

import toml

from romt import error


def target_matches_any(target: str, expected_targets: Iterable[str]) -> bool:
    if target == "*":
        return True
    for expected in expected_targets:
        if target == expected or expected == "*":
            return True
    return False


class Package:
    def __init__(
        self, name: str, target: str, details: MutableMapping[str, Any]
    ):
        self.name = name
        self.target = target
        self.available = details["available"]
        self.xz_url = details.get("xz_url", "")

    @property
    def has_rel_path(self) -> bool:
        return self.xz_url != ""

    @property
    def rel_path(self) -> str:
        if not self.has_rel_path:
            raise ValueError(
                "Package {}/{} missing xz_url".format(self.name, self.target)
            )
        url = self.xz_url
        prefix = "/dist/"
        return url[url.index(prefix) + len(prefix) :]


class Manifest:
    def __init__(self, raw_dict: MutableMapping[str, Any]):
        self._dict = raw_dict

    @staticmethod
    def from_toml_path(toml_path: Path) -> "Manifest":
        return Manifest(toml.load(toml_path))

    def clone(self) -> "Manifest":
        return Manifest(copy.deepcopy(self._dict))

    @property
    def _rust_src_version(self) -> str:
        version = self._dict["pkg"]["rust-src"]["version"]
        # Sample version lines found below [pkg.rust-src]:
        # version = "1.43.0-beta.5 (934ae7739 2020-04-06)"
        # version = "1.44.0-nightly (42abbd887 2020-04-07)"
        # version = "1.42.0 (b8cedc004 2020-03-09)"
        return version

    @property
    def channel(self) -> str:
        version = self._rust_src_version
        if "-beta" in version:
            channel = "beta"
        elif "-nightly" in version:
            channel = "nightly"
        else:
            channel = "stable"
        return channel

    @property
    def version(self) -> str:
        version = self._rust_src_version
        # version = "1.44.0-nightly (42abbd887 2020-04-07)"
        # version = "1.42.0 (b8cedc004 2020-03-09)"
        return version.split("-")[0].split()[0]

    @property
    def date(self) -> str:
        return self._dict["date"]

    @property
    def spec(self) -> str:
        return "{}-{}".format(self.channel, self.date)

    @property
    def ident(self) -> str:
        return "{}({})".format(self.spec, self.version)

    def set_package_available(
        self, package_name: str, target: str, available: bool = True
    ) -> None:
        details = self._dict["pkg"][package_name]["target"][target]
        if available and "xz_url" not in details:
            raise error.AbortError(
                "package {}/{} set available but missing xz_url".format(
                    package_name, target
                )
            )
        details["available"] = available

    def get_package(self, package_name: str, target: str) -> Package:
        details = self._dict["pkg"][package_name]["target"][target]
        return Package(package_name, target, details)

    def gen_packages(self) -> Generator[Package, None, None]:
        """Generate Package for all (name, target) in manifest."""
        for name, package_dict in self._dict["pkg"].items():
            for target in package_dict["target"].keys():
                yield self.get_package(name, target)

    def gen_available_packages(
        self, *, targets: Optional[Iterable[str]] = None
    ) -> Generator[Package, None, None]:
        """gen_packages() for available packages matching targets."""
        for package in self.gen_packages():
            if package.available:
                if targets is None or target_matches_any(
                    package.target, targets
                ):
                    yield package

    def available_packages(self) -> List[Package]:
        return list(self.gen_available_packages())

    def _targets_from_packages(self, packages: Iterable[Package]) -> List[str]:
        targets = set(p.target for p in packages)
        targets.discard("*")
        return sorted(targets)

    def all_targets(self) -> List[str]:
        return self._targets_from_packages(self.gen_packages())

    def available_targets(self) -> List[str]:
        return self._targets_from_packages(self.gen_available_packages())
