import collections
import copy
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    MutableMapping,
    Optional,
    Tuple,
)

import toml


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
        self.xz_url = str(details.get("xz_url", ""))

    def _fields(self) -> Tuple[str, str]:
        return (self.name, self.target)

    def __repr__(self) -> str:
        return f"Package {{ name={self.name}, target={self.target} }}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Package):
            return False
        return self._fields() == other._fields()

    def __hash__(self) -> int:
        return hash(self._fields())

    @property
    def has_rel_path(self) -> bool:
        return bool(self.xz_url != "")

    @property
    def rel_path(self) -> str:
        if not self.has_rel_path:
            raise ValueError(
                f"Package {self.name}/{self.target} missing xz_url"
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
        version = str(self._dict["pkg"]["rust-src"]["version"])
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
        return str(self._dict["date"])

    @property
    def spec(self) -> str:
        return f"{self.channel}-{self.date}"

    @property
    def ident(self) -> str:
        return f"{self.spec}({self.version})"

    def get_package(self, package_name: str, target: str) -> Package:
        details = self._dict["pkg"][package_name]["target"][target]
        return Package(package_name, target, details)

    def gen_all_packages(self) -> Generator[Package, None, None]:
        """Generate Package for all (name, target) in manifest."""
        for name, package_dict in self._dict["pkg"].items():
            for target in package_dict["target"].keys():
                yield self.get_package(name, target)

    def gen_available_packages(
        self,
        *,
        targets: Optional[Iterable[str]] = None,
        rel_path_is_present: Optional[Callable[[str], bool]] = None,
    ) -> Generator[Package, None, None]:
        """available packages matching targets and "present"."""
        if targets is None:
            target_list = ["*"]
        else:
            target_list = list(targets)
        for package in self.gen_all_packages():
            if (
                package.available
                and target_matches_any(package.target, target_list)
                and (
                    rel_path_is_present is None
                    or rel_path_is_present(package.rel_path)
                )
            ):
                yield package

    def all_targets(self) -> List[str]:
        targets = {p.target for p in self.gen_all_packages()}
        targets.discard("*")
        return sorted(targets)

    def available_targets(
        self,
        *,
        targets: Optional[Iterable[str]] = None,
        rel_path_is_present: Optional[Callable[[str], bool]] = None,
    ) -> List[str]:
        available_targets = {
            p.target
            for p in self.gen_available_packages(
                targets=targets,
                rel_path_is_present=rel_path_is_present,
            )
        }
        available_targets.discard("*")
        return sorted(available_targets)

    def available_target_types(
        self,
        *,
        targets: Optional[Iterable[str]] = None,
        rel_path_is_present: Optional[Callable[[str], bool]] = None,
    ) -> Dict[str, str]:
        target_packages = collections.defaultdict(set)
        rel_path_targets = collections.defaultdict(set)
        for package in self.gen_available_packages():
            # No need to discard the case `target == "*"`.
            target_packages[package.target].add(package)
            rel_path_targets[package.rel_path].add(package.target)

        target_types: Dict[str, str] = {}
        if targets is not None:
            target_list = list(targets)
        else:
            target_list = self.available_targets()
        for target in sorted(target_list):
            packages = target_packages[target]
            if not packages:
                continue
            have_all_rel_paths = True
            have_unique_rel_path = False
            have_rustc = False
            have_rust_std = False
            for package in packages:
                is_present = (
                    rel_path_is_present is None
                    or rel_path_is_present(package.rel_path)
                )
                if is_present:
                    if package.name == "rustc":
                        have_rustc = True
                    elif package.name == "rust-std":
                        have_rust_std = True
                    if len(rel_path_targets[package.rel_path]) == 1:
                        have_unique_rel_path = True
                else:
                    have_all_rel_paths = False
            if have_unique_rel_path or have_all_rel_paths:
                if have_rustc:
                    target_type = "native-target"
                elif have_rust_std:
                    target_type = "cross-target"
                else:
                    target_type = "minimal"
                target_types[target] = target_type

        return target_types
