import argparse
import os
import shutil
from pathlib import Path
from typing import (
    List,
    Set,
    Tuple,
)

import toml

from romt import base, common, dist, error, integrity

description = """\
Mirror and manage rustup tooling.
"""

epilog = """\

SPEC is one of:
  <version>
  stable
  latest
  *
Where:
- <version> is: X.Y.Z
- Multiple SPEC options may be given.
- Each SPEC option will be split at commas and whitespace.

TARGET is standard 3- or 4-tuple; common examples:
- x86_64-unknown-linux-gnu (alias ``linux``)
- x86_64-pc-windows-msvc (alias ``windows``)
- x86_64-apple-darwin (alias ``darwin``)

COMMAND values:

  download          download artifacts matching SPEC and TARGET to DEST
  verify            verify DEST artifacts matching SPEC and TARGET
  list              print DEST artifacts and targets matching SPEC
  all-targets       print all known targets (hard-coded; others are permitted)
  pack              pack DEST artifacts matching SPEC and TARGET into ARCHIVE
  unpack            unpack ARCHIVE into DEST, setting SPEC and TARGET
  fixup             fixup latest stable release with SPEC as candidate

When multiple COMMANDs are given, they share all option values.

For complete details, try ``romt --readme`` to view README.rst.
"""

RUSTUP_DEFAULT_URL = "https://static.rust-lang.org/rustup"


# Note: Known targets are found by inspecting the S3 tree, e.g.::
#  aws s3 ls --no-sign-request s3://static-rust-lang-org/rustup/archive/1.26.0/

ALL_KNOWN_TARGETS = """
    aarch64-apple-darwin
    aarch64-linux-android
    aarch64-pc-windows-msvc
    aarch64-unknown-linux-gnu
    aarch64-unknown-linux-musl
    arm-linux-androideabi
    arm-unknown-linux-gnueabi
    arm-unknown-linux-gnueabihf
    armv7-linux-androideabi
    armv7-unknown-linux-gnueabihf
    i686-apple-darwin
    i686-linux-android
    i686-pc-windows-gnu
    i686-pc-windows-msvc
    i686-unknown-linux-gnu
    mips-unknown-linux-gnu
    mips64-unknown-linux-gnuabi64
    mips64el-unknown-linux-gnuabi64
    mipsel-unknown-linux-gnu
    powerpc-unknown-linux-gnu
    powerpc64-unknown-linux-gnu
    powerpc64le-unknown-linux-gnu
    riscv64gc-unknown-linux-gnu
    s390x-unknown-linux-gnu
    x86_64-apple-darwin
    x86_64-linux-android
    x86_64-pc-windows-gnu
    x86_64-pc-windows-msvc
    x86_64-unknown-freebsd
    x86_64-unknown-illumos
    x86_64-unknown-linux-gnu
    x86_64-unknown-linux-musl
    x86_64-unknown-netbsd
    """.split()


def validate_spec(spec: str) -> str:
    """parse spec into (date, channel).

    SPEC is one of:
      <version>
      stable
      latest
      *
    Where:
    - <version> is: X.Y.Z
    - Multiple SPEC options may be given.
    - Each SPEC option will be split at commas and whitespace.

    """

    if spec in ("*", "latest", "stable") or common.is_version(spec):
        return spec

    raise error.UsageError(f"invalid SPEC {repr(spec)}")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    base.add_downloader_arguments(parser)

    parser.add_argument(
        "-s",
        "--select",
        action="append",
        dest="specs",
        metavar="SPEC",
        default=[],
        help="""one or more SPEC values for rustup selection""",
    )

    parser.add_argument(
        "-t",
        "--target",
        action="append",
        dest="targets",
        default=[],
        help="""target to download (default varies by COMMAND)""",
    )

    parser.add_argument(
        "--dest",
        action="store",
        default="rustup",
        help="""local download directory (default: %(default)s)""",
    )

    default_url = os.environ.get("RUSTUP_UPDATE_ROOT", RUSTUP_DEFAULT_URL)
    if default_url == RUSTUP_DEFAULT_URL:
        default_help = "; override default via env. var. `RUSTUP_UPDATE_ROOT`"
    else:
        default_help = (
            " from env. var. `RUSTUP_UPDATE_ROOT`;"
            f" otherwise default would be `{RUSTUP_DEFAULT_URL}`"
        )
    parser.add_argument(
        "--url",
        action="store",
        default=default_url,
        help=f"base URL of rustup (default: `%(default)s`{default_help})",
    )

    parser.add_argument(
        "--archive",
        action="store",
        metavar="ARCHIVE",
        default="rustup.tar.gz",
        help="use archive ARCHIVE for pack/unpack (default: %(default)s)",
    )

    parser.add_argument(
        "commands",
        nargs="*",
        metavar="COMMAND",
        help="""commands to execute in the order given""",
    )


class Main(dist.DistMain):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args)

    @property
    def release_stable_url_path(self) -> Tuple[str, Path]:
        rel_path = "release-stable.toml"
        release_stable_url = self.url_from_rel_path(rel_path)
        release_stable_path = self.dest_path_from_rel_path(rel_path)
        return release_stable_url, release_stable_path

    @property
    def release_stable_path(self) -> Path:
        _, path = self.release_stable_url_path
        return path

    def get_release_stable_version(self, *, download: bool) -> str:
        url, path = self.release_stable_url_path
        if download:
            # This file changes unexpectedly.  Avoid caching to ensure the
            # correct version is used.
            self.downloader.download_cached(url, path, cached=False)
        elif path.is_file():
            common.vprint(f"[read] {path}")
        else:
            raise error.MissingFileError(str(path))
        return str(toml.load(path)["version"])

    @property
    def artifact_root_rel_path(self) -> str:
        return "archive"

    @property
    def artifact_root_path(self) -> Path:
        return self.dest_path_from_rel_path(self.artifact_root_rel_path)

    def artifact_version_rel_path(self, version: str) -> str:
        return f"{self.artifact_root_rel_path}/{version}"

    def artifact_version_path(self, version: str) -> Path:
        return self.dest_path_from_rel_path(
            self.artifact_version_rel_path(version)
        )

    def rustup_init_rel_path(self, version: str, target: str) -> str:
        # archive/<version>/<target>/rustup-init[.exe]
        base_rel_path = "{}/{}/rustup-init".format(
            self.artifact_version_rel_path(version), target
        )
        rel_path = dist.append_exe_suffix(base_rel_path, target)
        return rel_path

    def version_from_spec(self, spec: str, *, download: bool) -> str:
        if spec == "stable":
            return self.get_release_stable_version(download=download)
        else:
            return spec

    def downloaded_versions(self) -> List[str]:
        versions = [p.name for p in self.artifact_root_path.glob("*")]
        return common.reverse_sorted_versions(versions)

    def adjust_download_specs(self, specs: List[str]) -> List[str]:
        # For downloads, wildcards not permitted.
        for spec in specs:
            validate_spec(spec)
            if spec == "*" or spec == "latest":
                raise error.UsageError(f"invalid wild SPEC: {spec}")
        return dist.require_specs(specs)

    def expand_wild_spec(self, spec: str) -> List[str]:
        specs: List[str] = []
        validate_spec(spec)
        if spec == "*":
            specs.extend(self.downloaded_versions())

        elif spec == "latest":
            found_versions = self.downloaded_versions()
            if found_versions:
                specs.append(found_versions[0])

        else:
            specs.append(spec)

        if not specs:
            raise error.UsageError(f"no matches for wild SPEC {repr(spec)}")

        return specs

    def adjust_wild_specs(self, specs: List[str]) -> List[str]:
        # For non-downloads, handle wild specs.
        adjusted_specs = []
        for spec in specs:
            adjusted_specs.extend(self.expand_wild_spec(spec))
        return dist.require_specs(adjusted_specs)

    def downloaded_targets(self, version: str) -> List[str]:
        target_paths = common.gen_dirs(self.artifact_version_path(version))
        return sorted(t.name for t in target_paths)

    def adjust_targets(
        self, version: str, base_targets: List[str]
    ) -> List[str]:
        targets = set()
        known_targets = set(ALL_KNOWN_TARGETS)
        for target in base_targets:
            if target == "all":
                targets.update(known_targets)
            elif target == "*":
                targets.update(self.downloaded_targets(version))
            else:
                if target not in known_targets:
                    common.eprint(f"warning: unknown target {repr(target)}")
                targets.add(target)
        return sorted(targets)

    def _download_verify(
        self, download: bool, specs: List[str], base_targets: List[str]
    ) -> None:
        for spec in specs:
            common.iprint(
                "{}: {}".format("Download" if download else "Verify", spec)
            )
            version = self.version_from_spec(spec, download=download)
            common.iprint(f"  version: {version}")

            targets = self.adjust_targets(version, base_targets)
            common.iprint(f"  targets: {len(targets)}")
            for t in targets:
                common.vvprint(f"  target: {t}")

            for target in targets:
                rel_path = self.rustup_init_rel_path(version, target)
                dest_path = self.dest_path_from_rel_path(rel_path)
                dest_url = self.url_from_rel_path(rel_path)
                if download:
                    self.downloader.download_verify(
                        dest_url, dest_path, assume_ok=self.args.assume_ok
                    )
                else:
                    self.downloader.verify(dest_path)

    def cmd_download(self) -> None:
        specs = self.adjust_download_specs(self.specs)
        base_targets = dist.require_targets(self.targets)
        self._download_verify(
            download=True, specs=specs, base_targets=base_targets
        )

    def cmd_verify(self) -> None:
        specs = self.adjust_wild_specs(self.specs)
        base_targets = dist.require_targets(self.targets, default="*")
        self._download_verify(
            download=False, specs=specs, base_targets=base_targets
        )

    def cmd_list(self) -> None:
        max_verbosity = common.get_max_verbosity()
        show_details = max_verbosity >= common.VERBOSITY_INFO
        for spec in self.adjust_wild_specs(self.specs):
            common.iprint(f"List: {spec}")
            version = self.version_from_spec(spec, download=False)
            if show_details:
                targets = self.downloaded_targets(version)

                target_out = f"targets[{len(targets)}]"
                # Example output:
                #   1.41.0   targets[84]
                common.iprint(f"{version:8} {target_out}")
                for target in targets:
                    common.iprint(f"  {target}")
            else:
                common.eprint(version)

    def cmd_all_targets(self) -> None:
        common.iprint("All known targets:")
        for target in ALL_KNOWN_TARGETS:
            common.eprint(target)

    def cmd_pack(self) -> None:
        base_targets = dist.require_targets(self.targets, default="*")
        archive_path = self.get_archive_path()
        common.iprint(f"Packing archive: {archive_path}")
        with common.tar_context(archive_path, "w") as tar_f:

            def pack_path(rel_path: str) -> None:
                dest_path = self.dest_path_from_rel_path(rel_path)
                packed_name = "rustup/" + rel_path
                common.vprint(f"[pack] {rel_path}")
                try:
                    tar_f.add(str(dest_path), packed_name)
                except FileNotFoundError:
                    raise error.MissingFileError(str(dest_path))

            def pack_rel_path(rel_path: str) -> None:
                pack_path(rel_path)
                pack_path(integrity.append_hash_suffix(rel_path))

            for spec in self.adjust_wild_specs(self.specs):
                common.iprint(f"Pack: {spec}")
                version = self.version_from_spec(spec, download=False)
                common.iprint(f"  version: {version}")

                targets = self.adjust_targets(version, base_targets)
                common.iprint(f"  targets: {len(targets)}")
                for t in targets:
                    common.vvprint(f"  target: {t}")

                for target in targets:
                    rel_path = self.rustup_init_rel_path(version, target)
                    pack_rel_path(rel_path)

    def _detect_version_targets(
        self, rel_paths: Set[str]
    ) -> Tuple[List[str], List[str]]:
        # rel_paths should be: "archive/<version>/<target>/<file>".
        versions = set()
        targets = set()
        for p in rel_paths:
            parts = p.split("/")
            if len(parts) < 4:
                common.eprint(f"warning: unexpected path {p}")
            else:
                version = parts[1]
                target = parts[2]
                if common.is_version(version):
                    versions.add(version)
                    targets.add(target)
        return sorted(versions), sorted(targets)

    def cmd_unpack(self) -> None:
        archive_path = self.get_archive_path()
        common.iprint(f"Unpacking archive: {archive_path}")
        rustup_prefix = "rustup/"
        prefix = f"{rustup_prefix}{self.artifact_root_rel_path}/"
        extracted = set()
        with common.tar_context(archive_path, "r") as tar_f:
            for tar_info in tar_f:
                if tar_info.isdir():
                    continue
                if not tar_info.name.startswith(prefix):
                    raise error.UnexpectedArchiveMemberError(tar_info.name)

                rel_path = tar_info.name[len(rustup_prefix) :]
                dest_path = self.dest_path_from_rel_path(rel_path)
                tar_info.name = str(dest_path)
                common.vprint(f"[unpack] {rel_path}")
                tar_f.extract(tar_info, set_attrs=False)
                extracted.add(rel_path)

        specs, targets = self._detect_version_targets(extracted)

        common.iprint(f"Unpacked specs: {len(specs)}")
        for spec in specs:
            common.iprint(f"  {spec}")

        common.iprint(f"Unpacked targets: {len(targets)}")
        for target in targets:
            common.iprint(f"  {target}")

        self.specs = specs
        self.targets = targets

    def _write_release_stable(self, version: str) -> None:
        path = self.release_stable_path
        toml_dict = {"schema-version": "1", "version": version}
        with path.open("w") as f:
            toml.dump(toml_dict, f)

    def _fixup_version(self, version: str) -> None:
        # Write release_stable unless a newer one already exists.
        path = self.release_stable_path
        if path.is_file():
            old_version = self.get_release_stable_version(download=False)
            new_key = common.version_sort_key(version)
            old_key = common.version_sort_key(old_version)
            write = new_key >= old_key
        else:
            write = True
        if write:
            common.iprint(f"[write] {path} (version={version})")
            self._write_release_stable(version)

    def cmd_fixup(self) -> None:
        for spec in self.adjust_wild_specs(self.specs):
            common.iprint(f"Fixup: {spec}")
            version = self.version_from_spec(spec, download=False)
            version_path = self.artifact_version_path(version)
            # Artifacts are arranged as: <version_path>/<target>/<artifact>
            # If no artifacts exist for any targets, claim the version
            # is not present.
            artifacts = list(version_path.glob("*/*"))
            if not artifacts:
                raise error.UsageError(f"version {version} not present")
            self._fixup_version(version)

        # Copy rustup/archive/<stable_version>/ to rustup/dist/.
        stable_version = self.get_release_stable_version(download=False)

        archive_version_path = self.dest_path_from_rel_path(
            f"archive/{stable_version}"
        )
        if not archive_version_path.is_dir():
            raise error.MissingDirectoryError(str(archive_version_path))

        dist_path = self.dest_path_from_rel_path("dist")
        if dist_path.is_dir():
            shutil.rmtree(str(dist_path))

        common.iprint(f"[copytree] {archive_version_path} -> {dist_path}")
        shutil.copytree(str(archive_version_path), str(dist_path))

    def _run(self) -> None:
        valid_commands = [
            "download",
            "verify",
            "list",
            "all-targets",
            "pack",
            "unpack",
            "fixup",
        ]
        commands = self.args.commands
        if commands:
            base.verify_commands(commands, valid_commands)
        else:
            common.iprint("nothing to do; try a COMMAND")

        for cmd in commands:
            if cmd == "download":
                self.cmd_download()
                self.cmd_fixup()

            elif cmd == "verify":
                self.cmd_verify()

            elif cmd == "list":
                self.cmd_list()

            elif cmd == "all-targets":
                self.cmd_all_targets()

            elif cmd == "pack":
                self.cmd_pack()

            elif cmd == "unpack":
                self.cmd_unpack()
                self.cmd_verify()
                self.cmd_fixup()

            elif cmd == "fixup":
                self.cmd_fixup()
