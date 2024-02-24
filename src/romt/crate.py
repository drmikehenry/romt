import argparse
import enum
import json
import os
import re
import shutil
import tempfile
import typing
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

# Using `try/except` here to prevent this lint warning caused by setting the
# environment variable before subsequent imports::
#   "E402 Module level import not at top of file".
try:
    # Without this environment variable, importing `git` will cause failure
    # when the `git` command is not found.  We want to defer the probe for Git
    # until we know we need it (whenever we acquire a `git.Repo` instance).
    os.environ["GIT_PYTHON_REFRESH"] = "quiet"
    import git
except ImportError:
    # We're not actually trying to catch any exception; just dodging a linter
    # warning.
    raise
import git.objects
import git.remote
import toml
import trio

import romt.download
from romt import base, common, error

# Name of index:
INDEX_NAME = "crates.io-index"


# Standard location for index repository:
INDEX_STANDARD_PATH = Path("git") / INDEX_NAME


# Name of index bundle file:
INDEX_BUNDLE_NAME = "origin.bundle"


# Name of index bundle within archive:
INDEX_BUNDLE_PACKED_NAME = "{}/{}".format(
    INDEX_STANDARD_PATH.as_posix(), INDEX_BUNDLE_NAME
)


description = """\
Mirror and manage crates from crates.io.
"""

epilog = """\
COMMAND values:
  Initial setup:
    init            setup INDEX and CRATES_ROOT for download/export scenario
    init-import     setup INDEX and CRATES_ROOT for import scenario
    config          edit INDEX/config.json to point to mirror server
  Routine updates:
    update          alias for ``pull download mark``
    export          alias for ``pull download pack mark``
    import          alias for ``unpack pull verify mark``
  Less common:
    pull            pull {INDEX_NAME} commits from origin into INDEX
    download        download .crate files to CRATES_ROOT across RANGE
    verify          verify .crate files in CRATES_ROOT across RANGE
    pack            pack RANGE of crates and INDEX commits into ARCHIVE
    mark            set branch ``mark`` to match END of RANGE
    unpack          unpack {INDEX_BUNDLE_NAME} and CRATES_ROOT from ARCHIVE
    list            print crate names across RANGE

When multiple COMMANDs are given, they share all option values.

For complete details, try ``romt --readme`` to view README.rst.
""".format(INDEX_NAME=INDEX_NAME, INDEX_BUNDLE_NAME=INDEX_BUNDLE_NAME)


class PrefixStyle(enum.Enum):
    LOWER = enum.auto()
    MIXED = enum.auto()

    @classmethod
    def from_config_str(cls, config_str: str) -> "PrefixStyle":
        if config_str == "lower":
            return cls.LOWER
        assert config_str == "mixed"
        return cls.MIXED

    def to_config_str(self) -> str:
        if self is PrefixStyle.LOWER:
            return "lower"
        assert self is PrefixStyle.MIXED
        return "mixed"


CratesConfig = Dict[str, Any]


def _crates_config_prefix_style(crates_config: CratesConfig) -> PrefixStyle:
    if crates_config["prefix"] == "mixed":
        return PrefixStyle.MIXED
    return PrefixStyle.LOWER


def _crates_config_archive_prefix_style(
    crates_config: CratesConfig,
) -> PrefixStyle:
    if crates_config["archive_prefix"] == "mixed":
        return PrefixStyle.MIXED
    return PrefixStyle.LOWER


def _get_crates_config_path(crates_root_path: Path) -> Path:
    return crates_root_path / "config.toml"


def _legacy_crates_config() -> CratesConfig:
    return {"prefix": "mixed", "archive_prefix": "mixed"}


def _default_crates_config() -> CratesConfig:
    return {"prefix": "lower", "archive_prefix": "mixed"}


def _write_crates_config(
    crates_root_path: Path, crates_config: CratesConfig
) -> None:
    crates_config_path = _get_crates_config_path(crates_root_path)
    with crates_config_path.open("w") as f:
        toml.dump(crates_config, f)


def _read_crates_config(crates_root_path: Path) -> CratesConfig:
    crates_config_path = _get_crates_config_path(crates_root_path)
    if crates_config_path.is_file():
        crates_config = _default_crates_config()
        with crates_config_path.open() as f:
            toml_dict = toml.loads(f.read())
        if not isinstance(toml_dict, dict):
            common.abort(f"invalid config structure in {crates_root_path}")
        for key in toml_dict:
            if key not in crates_config:
                common.abort(f"invalid key {key} in {crates_root_path}")
        crates_config.update(toml_dict)
    else:
        crates_config = _legacy_crates_config()
    return crates_config


def _prevent_mixed_with_case_insensitive(crates_root_path: Path) -> None:
    """Raise error.AbortError if MIXED prefixes on case-insensitive share."""

    # If config file is missing, do not prevent legacy access.
    if not _get_crates_config_path(crates_root_path).is_file():
        return

    crates_config = _read_crates_config(crates_root_path)
    prefix_style = _crates_config_prefix_style(crates_config)
    if prefix_style is PrefixStyle.MIXED:
        config_path = _get_crates_config_path(crates_root_path)
        upper_config_path = config_path.with_name(config_path.name.upper())
        if upper_config_path.exists():
            common.eprint(
                "Cannot use mixed-case prefix on case-insensitive share"
            )
            raise error.AbortError


def crate_name_version_from_rel_path(rel_path: str) -> Tuple[str, str]:
    m = re.search(
        r"""
        /
        (?P<name> [^/]+)
        /
        (?P=name) - (?P<version> [^/]+) \.crate
        $
        """,
        rel_path,
        re.VERBOSE,
    )
    if m:
        return m.group("name"), m.group("version")
    return "", ""


def crate_prefix_from_name(name: str, prefix_style: PrefixStyle) -> str:
    if len(name) == 1:
        prefix = "1"
    elif len(name) == 2:
        prefix = "2"
    elif len(name) == 3:
        prefix = f"3/{name[0]}"
    else:
        prefix = f"{name[:2]}/{name[2:4]}"
    if prefix_style is PrefixStyle.LOWER:
        prefix = prefix.lower()
    return prefix


def crate_basename_from_name_version(name: str, version: str) -> str:
    return f"{name}-{version}.crate"


def crate_rel_path_from_name_version(
    name: str, version: str, prefix_style: PrefixStyle
) -> Path:
    prefix = crate_prefix_from_name(name, prefix_style)
    basename = crate_basename_from_name_version(name, version)
    return Path(prefix) / name / basename


def blobs_in_commit_range(
    start_commit: Optional[git.objects.Commit], end_commit: git.objects.Commit
) -> Generator[Tuple[str, bytes, bytes], None, None]:
    """Generate (blob_path, start_blob, end_blob)."""
    if start_commit is not None:
        for diff in end_commit.diff(start_commit):
            # diff.a_xxx goes with end_commit.
            if diff.a_blob:
                a_blob = diff.a_blob.data_stream.read()
                if diff.b_blob:
                    b_blob = diff.b_blob.data_stream.read()
                else:
                    b_blob = b""
                yield diff.a_path, b_blob, a_blob
    else:
        for item in end_commit.tree.traverse():
            if getattr(item, "type") == "blob":
                blob = typing.cast(git.objects.Blob, item)
                yield str(blob.path), b"", blob.data_stream.read()


class Crate:
    def __init__(self, name: str, version: str, hash: str):
        self.name = name
        self.version = version
        self.hash = hash

    def __str__(self) -> str:
        return f"Crate({self.name}, {self.version}, {self.hash})"

    @property
    def ident(self) -> Tuple[str, str]:
        return self.name, self.version

    def prefix(self, prefix_style: PrefixStyle) -> str:
        return crate_prefix_from_name(self.name, prefix_style)

    def basename(self) -> str:
        return crate_basename_from_name_version(self.name, self.version)

    def rel_path(self, prefix_style: PrefixStyle) -> Path:
        return crate_rel_path_from_name_version(
            self.name, self.version, prefix_style
        )


def blob_lines(blob: bytes) -> Generator[str, None, None]:
    yield from blob.decode("utf8").splitlines()


def crate_from_text(line: str) -> Crate:
    j = json.loads(line)
    return Crate(j["name"], j["vers"], j["cksum"])


def blob_crates(blob: bytes) -> Generator[Crate, None, None]:
    d = {}
    for line in blob_lines(blob):
        crate = crate_from_text(line)
        d[crate.version] = crate
    for crate in d.values():
        yield crate


def crates_in_commit_range(
    start_commit: Optional[git.objects.Commit], end_commit: git.objects.Commit
) -> Generator[Crate, None, None]:
    """Generate newly specified crates."""

    rex = re.compile(
        r"""
        ^ 1/ [^/] $
        |
        ^ 2/ [^/]{2} $
        |
        ^ 3/ [^/] / [^/]{3} $
        |
        ^ [^/]{2} / [^/]{2} / [^/]{4,} $
        """,
        re.VERBOSE,
    )
    for path, start_blob, end_blob in blobs_in_commit_range(
        start_commit, end_commit
    ):
        if not rex.search(path):
            continue
        old_versions = {crate.version for crate in blob_crates(start_blob)}
        for crate in blob_crates(end_blob):
            if crate.version not in old_versions:
                yield crate


def crates_in_range(
    repo: git.Repo, start: str, end: str
) -> Generator[Crate, None, None]:
    try:
        start_commit = repo.commit(start) if start else None
        end_commit = repo.commit(end)
    except git.exc.BadName as e:
        raise error.GitError(f"bad commit requested: {e}")
    yield from crates_in_commit_range(start_commit, end_commit)


def git_bundle_create(
    repo: git.Repo, bundle_file_name: str, start: str, end: str
) -> None:
    args = [
        "create",
        bundle_file_name,
    ]
    if start:
        args.append("^" + start)
    if end == "master":
        bundle_end = end
    else:
        repo.create_head("bundle/master", end, force=True)
        bundle_end = "bundle/master"
    args.append(bundle_end)
    repo.git.bundle(args)


def get_index_path(index: str) -> Path:
    path = Path(index)
    if not path.is_dir():
        raise error.UsageError(f"{path} is not a valid index directory")
    return path


def get_repo(index: str) -> git.Repo:
    path = get_index_path(index)
    repo = git.Repo(str(path))
    try:
        repo.git.version()
    except git.exc.GitCommandNotFound:
        raise error.GitError(
            "`git` command not found; Git is required for this operation"
        )
    return repo


def get_crates_root_path(crates_root: str) -> Path:
    path = Path(crates_root)
    if not path.is_dir():
        raise error.UsageError(f"{path} is not a valid crates directory")
    return path


def fetch_origin(repo: git.Repo) -> None:
    origin = git.remote.Remote(repo, "origin")
    origin.fetch(force=True)
    repo.create_head("origin_master", "remotes/origin/master", force=True)


def get_origin_url(repo: git.Repo) -> str:
    origin = git.remote.Remote(repo, "origin")
    urls = list(origin.urls)
    if len(urls) == 1:
        return urls[0]
    else:
        raise error.UsageError(
            "INDEX remote ``origin`` must have exactly one ``URL``"
        )


def mark(repo: git.Repo, end: str) -> None:
    for branch in ["mark", "master"]:
        if branch == repo.head.reference.name:
            common.eprint(
                "Will not move branch {} (it is current HEAD)".format(
                    repr(branch)
                )
            )
        else:
            common.iprint(
                f"Move branch {repr(branch)} to point to {repr(end)}"
            )
            repo.create_head(f"refs/heads/{branch}", end, force=True)


def list_crates(crates: List[Crate]) -> None:
    for crate in crates:
        common.iprint(crate.basename())


def _process_crates(
    downloader: romt.download.Downloader,
    dl_template: Optional[str],
    crates: List[Crate],
    crates_root: Path,
    good_paths_log_path: str,
    bad_paths_log_path: str,
    *,
    keep_going: bool,
    assume_ok: bool,
) -> None:
    good_paths_file = common.open_optional(good_paths_log_path, "w")
    bad_paths_file = common.open_optional(bad_paths_log_path, "w")

    num_good_paths = 0
    num_bad_paths = 0

    limiter = downloader.new_limiter()

    crates_config = _read_crates_config(crates_root)
    prefix_style = _crates_config_prefix_style(crates_config)

    async def _process_one(crate: Crate) -> None:
        nonlocal num_good_paths, num_bad_paths
        rel_path = crate.rel_path(prefix_style)
        path = crates_root / rel_path
        prefix = crate_prefix_from_name(crate.name, PrefixStyle.MIXED)
        lower_prefix = crate_prefix_from_name(crate.name, PrefixStyle.LOWER)
        is_good = False
        try:
            if dl_template is None:
                downloader.verify_hash(path, crate.hash)
            else:
                url = dl_template.format(
                    crate=crate.name,
                    version=crate.version,
                    prefix=prefix,
                    lowerprefix=lower_prefix,
                )
                await downloader.adownload_verify_hash(
                    url, path, crate.hash, assume_ok=assume_ok
                )
            is_good = True
        except error.DownloadError as e:
            common.eprint(e)
        except error.MissingFileError as e:
            common.eprint(e)
        except error.IntegrityError as e:
            common.eprint(e)

        if is_good:
            num_good_paths += 1
            common.log(good_paths_file, path)
        else:
            num_bad_paths += 1
            common.log(bad_paths_file, path)

        limiter.release_on_behalf_of(crate)

    async def _process_inner() -> None:
        async with trio.open_nursery() as nursery:
            for crate in crates:
                await limiter.acquire_on_behalf_of(crate)
                nursery.start_soon(
                    _process_one,
                    crate,
                )

    downloader.run_job(_process_inner)

    common.iprint(f"{num_bad_paths} bad paths, {num_good_paths} good paths")

    common.close_optional(good_paths_file)
    common.close_optional(bad_paths_file)

    if num_bad_paths > 0 and not keep_going:
        raise error.AbortError()


def download_crates(
    downloader: romt.download.Downloader,
    dl_template: str,
    crates: List[Crate],
    crates_root: Path,
    good_paths_log_path: str,
    bad_paths_log_path: str,
    *,
    keep_going: bool,
    assume_ok: bool,
) -> None:
    _process_crates(
        downloader,
        dl_template,
        crates,
        crates_root,
        good_paths_log_path,
        bad_paths_log_path,
        keep_going=keep_going,
        assume_ok=assume_ok,
    )


def verify_crates(
    downloader: romt.download.Downloader,
    crates: List[Crate],
    crates_root: Path,
    good_paths_log_path: str,
    bad_paths_log_path: str,
    *,
    keep_going: bool,
    assume_ok: bool,
) -> None:
    _process_crates(
        downloader,
        None,
        crates,
        crates_root,
        good_paths_log_path,
        bad_paths_log_path,
        keep_going=keep_going,
        assume_ok=assume_ok,
    )


def pack(
    crates: List[Crate],
    crates_root: Path,
    bundle_path: Optional[Path],
    archive_path: Path,
    keep_going: bool,
) -> None:
    num_good_paths = 0
    num_bad_paths = 0

    crates_config = _read_crates_config(crates_root)
    prefix_style = _crates_config_prefix_style(crates_config)
    archive_prefix_style = _crates_config_archive_prefix_style(crates_config)

    with common.tar_context(archive_path, "w") as tar_f:
        archive_format = b"1\n"
        if archive_prefix_style == PrefixStyle.LOWER:
            archive_format = b"2\n"
        with tempfile.NamedTemporaryFile() as f:
            f.write(archive_format)
            f.flush()
            tar_f.add(f.name, "ARCHIVE_FORMAT")

        if bundle_path is not None:
            packed_name = INDEX_BUNDLE_PACKED_NAME
            common.vprint(f"[pack] {packed_name}")
            tar_f.add(str(bundle_path), packed_name)

        for crate in sorted(crates, key=lambda crate: crate.ident):
            path = crates_root / crate.rel_path(prefix_style)
            packed_rel_path = crate.rel_path(archive_prefix_style)
            packed_name = "crates/" + packed_rel_path.as_posix()
            try:
                common.vprint(f"[pack] {crate.basename()}")
                tar_f.add(str(path), packed_name)
                num_good_paths += 1
            except FileNotFoundError:
                num_bad_paths += 1
                common.eprint(f"Error: Missing {crate.basename()}")
                if not keep_going:
                    raise error.AbortError()

    common.iprint(f"{num_bad_paths} bad paths, {num_good_paths} good paths")


def unpack(
    repo: git.Repo,
    crates_root: Path,
    bundle_path: Path,
    archive_path: Path,
    keep_going: bool,
) -> None:
    num_crates = 0
    crates_prefix = "crates/"
    found_bundle = False

    crates_config = _read_crates_config(crates_root)
    prefix_style = _crates_config_prefix_style(crates_config)
    archive_prefix_style = PrefixStyle.MIXED
    found_file = False

    with common.tar_context(archive_path, "r") as tar_f:
        for tar_info in tar_f:
            if tar_info.isdir():
                continue
            elif tar_info.name == "ARCHIVE_FORMAT":
                if found_file:
                    common.abort(
                        "Unexpected ARCHIVE_FORMAT (not at archive start)"
                    )

                found_file = True
                reader = tar_f.extractfile(tar_info)
                if reader is None:
                    common.abort("Invalid ARCHIVE_FORMAT (unreadable)")

                archive_format = reader.read().decode(errors="replace").strip()
                if archive_format == "1":
                    archive_prefix_style = PrefixStyle.MIXED
                elif archive_format == "2":
                    archive_prefix_style = PrefixStyle.LOWER
                else:
                    common.abort(f"Invalid ARCHIVE_FORMAT {archive_format!r}")
                common.vprint(f"Detected archive_format {archive_format} ")

            elif tar_info.name == INDEX_BUNDLE_PACKED_NAME:
                found_file = True
                found_bundle = True
                tar_info.name = str(bundle_path)
                common.vprint(f"[unpack] {tar_info.name}")
                # Use the "fully_trusted" filter for this member because we're
                # overriding the destination path to the correct value.
                # (Otherwise, `.extract()` will not allow absolute paths for
                # `tarinfo.name`).
                tar_f.extract(
                    tar_info, set_attrs=False, filter="fully_trusted"
                )

            elif tar_info.name.startswith(crates_prefix):
                found_file = True
                name, version = crate_name_version_from_rel_path(tar_info.name)
                if not name or not version:
                    common.abort(f"Invalid crate {tar_info.name}")
                expected_rel_path = crate_rel_path_from_name_version(
                    name, version, archive_prefix_style
                ).as_posix()
                actual_rel_path = tar_info.name[len(crates_prefix) :]
                if actual_rel_path != expected_rel_path:
                    common.abort(
                        f"Unexpected crate prefix for {tar_info.name}"
                    )

                rel_path = crate_rel_path_from_name_version(
                    name, version, prefix_style
                )
                tar_info.name = str(rel_path)
                common.vprint(f"[unpack] {os.path.basename(tar_info.name)}")
                tar_f.extract(tar_info, str(crates_root), set_attrs=False)
                num_crates += 1

            else:
                common.abort(f"Unexpected archive member {tar_info.name}")

    if not found_bundle:
        common.abort(f"Missing {INDEX_BUNDLE_PACKED_NAME} in archive")

    common.iprint(f"{num_crates} extracted crates")


def _config_json_path(repo: git.Repo) -> Path:
    if repo.working_tree_dir is None:
        raise error.UsageError("INDEX lacks a work tree")
    working_tree = Path(repo.working_tree_dir)
    config_path = working_tree / "config.json"
    return config_path


def read_config_json(repo: git.Repo) -> Optional[bytes]:
    config_path = _config_json_path(repo)
    initial_config: Optional[bytes] = None
    if config_path.is_file():
        initial_config = config_path.read_bytes()
    return initial_config


def update_config_json(repo: git.Repo, config: bytes) -> None:
    old_config = read_config_json(repo)
    if old_config is None or config != old_config:
        config_path = _config_json_path(repo)
        common.vprint(f"update-config: {config_path}")
        config_path.write_bytes(config)
        repo.index.add(str(config_path))
        repo.index.commit("Apply config.json adjustments")


def _upgrade_to_working(repo: git.Repo) -> None:
    working = git.Reference(repo, "refs/heads/working")
    if repo.head.reference.name != "working" and not working.is_valid():
        # Time to upgrade working tree to use "working" branch.
        common.eprint("""Upgrade index to use "working" branch as HEAD""")
        if repo.head.reference.is_valid():
            # Create "working" branch based on current HEAD.
            common.iprint(
                """Checkout new "working" branch from current HEAD"""
            )
            repo.create_head("refs/heads/working", "HEAD")
        repo.head.set_reference(working)


def merge_origin_master(repo: git.Repo) -> None:
    _upgrade_to_working(repo)
    initial_config = read_config_json(repo)

    try:
        common.vprint("merge-index: merge origin/master")
        repo.git.merge("remotes/origin/master", "-m", "Merge origin/master")
    except git.GitError:
        common.iprint("merge-index: merge failed; reconstructing")
        common.vprint("merge-index: reset to recover failed merge state")
        repo.head.reset(working_tree=True, index=True)
        common.vprint("merge-index: reset to remotes/origin/master")
        repo.head.reset("remotes/origin/master", working_tree=True, index=True)

    # Restore initial_config if necessary.
    if initial_config is not None:
        update_config_json(repo, initial_config)


def _init_common(
    index_path: Path,
    origin_location: str,
    crates_root_path: Path,
    prefix_style: PrefixStyle,
) -> git.Repo:
    if index_path.exists():
        raise error.UsageError(
            f"index directory {repr(str(index_path))} already exists"
        )
    if crates_root_path.exists():
        raise error.UsageError(
            "crates directory {} already exists".format(
                repr(str(crates_root_path))
            )
        )
    common.iprint(f"create crates directory at {repr(str(crates_root_path))}:")
    crates_root_path.mkdir(parents=True)
    crates_config = _default_crates_config()
    crates_config["prefix"] = prefix_style.to_config_str()
    _write_crates_config(crates_root_path, crates_config)

    # Disallow MIXED style on case-insensitive filesystem:
    try:
        _prevent_mixed_with_case_insensitive(crates_root_path)
    except error.AbortError:
        shutil.rmtree(crates_root_path)
        raise

    common.iprint(f"create index repository at {repr(str(index_path))}:")
    index_path.mkdir(parents=True)
    repo = git.Repo.init(str(index_path))
    common.iprint(f"  remote add origin {origin_location}")
    repo.create_remote("origin", origin_location)

    # Setup "HEAD" to new "working" branch.
    working = git.Reference(repo, "refs/heads/working")
    repo.head.set_reference(working)

    # Setup default remote and merge branch for "working".
    with repo.config_writer() as writer:
        writer.set_value('branch "working"', "remote", "origin")
        writer.set_value('branch "working"', "merge", "refs/heads/master")
    return repo


def init(
    index_path: Path,
    index_url: str,
    crates_root_path: Path,
    prefix_style: PrefixStyle,
) -> None:
    _init_common(index_path, index_url, crates_root_path, prefix_style)


def init_import(
    index_path: Path, crates_root_path: Path, prefix_style: PrefixStyle
) -> None:
    bundle_path = index_path / INDEX_BUNDLE_NAME
    bundle_location = str(bundle_path.absolute())
    repo = _init_common(
        index_path, bundle_location, crates_root_path, prefix_style
    )
    with repo.config_writer() as writer:
        writer.set_value(
            'remote "origin"', "fetch", "+refs/heads/*:refs/remotes/origin/*"
        )
        writer.add_value(
            'remote "origin"',
            "fetch",
            "+refs/heads/bundle/*:refs/remotes/origin/*",
        )


def configure_index(repo: git.Repo, server_url: str) -> None:
    if not server_url.endswith("/"):
        server_url += "/"
    config = """\
{{
    "dl": "{}",
    "api": "{}"
}}
""".format(server_url + "crates/{crate}/{crate}-{version}.crate", server_url)
    update_config_json(repo, config.encode("utf-8"))


def add_arguments(parser: argparse.ArgumentParser) -> None:
    base.add_downloader_arguments(parser)

    parser.add_argument(
        "--index",
        action="store",
        default=str(INDEX_STANDARD_PATH),
        help="""{INDEX_NAME} repository path (default: %(default)s)""".format(
            INDEX_NAME=INDEX_NAME
        ),
    )

    parser.add_argument(
        "--crates",
        action="store",
        metavar="CRATES_ROOT",
        default="crates",
        help="directory holding the crates (default: %(default)s)",
    )

    parser.add_argument(
        "--start",
        action="store",
        help="""reference to start of RANGE (``0`` for start of repo);
            if not provided START defaults to ``mark`` and
            --allow-missing-start is implied""",
    )

    parser.add_argument(
        "--end",
        action="store",
        default="HEAD",
        help="reference to end of RANGE (default: %(default)s)",
    )

    parser.add_argument(
        "--allow-missing-start",
        action="store_true",
        help="treat non-existent START as start of repo instead of an error",
    )

    parser.add_argument(
        "--good-paths",
        action="store",
        metavar="GOOD_PATHS",
        help="record successful paths to file GOOD_PATHS",
    )

    parser.add_argument(
        "--bad-paths",
        action="store",
        metavar="BAD_PATHS",
        help="record bad paths to file BAD_PATHS",
    )

    parser.add_argument(
        "--archive",
        action="store",
        default="crates.tar.gz",
        help="use file ARCHIVE for pack/unpack (default: %(default)s)",
    )

    parser.add_argument(
        "--keep-going",
        action="store_true",
        default=False,
        help="keep going even if errors occur (helps with missing crates)",
    )

    parser.add_argument(
        "--crates-url",
        action="store",
        default=(
            "https://static.crates.io/crates/{crate}/{crate}-{version}.crate"
        ),
        help="""template for crates download URL for ``download`` command;
            use {crate} and {version} to parametrize with crate's name
            and version number; to use the API as defined in
            crates.io-index/config.json, use
            "https://crates.io/api/v1/crates/{crate}/{version}/download";
            default=%(default)s
        """,
    )

    parser.add_argument(
        "--index-url",
        action="store",
        default="https://github.com/rust-lang/crates.io-index",
        help="""URL of upstream crates.io-index Git repository
            for ``init`` (default: %(default)s)""",
    )

    parser.add_argument(
        "--bundle-path",
        action="store",
        help="""local path to store {INDEX_BUNDLE_NAME} for ``pack``,
            ``unpack``; configures path to origin repo for ``init-import``;
            (default: INDEX/{INDEX_BUNDLE_NAME})""".format(
            INDEX_BUNDLE_NAME=INDEX_BUNDLE_NAME
        ),
    )

    parser.add_argument(
        "--server-url",
        action="store",
        default=("http://localhost:8000"),
        help="""base URL for server configured into INDEX/config.json by
            ``config`` command (default=%(default)s)
        """,
    )

    parser.add_argument(
        "--prefix",
        dest="prefix_style",
        choices=["mixed", "lower"],
        default="lower",
        help="crate path prefix style (default=%(default)s)",
    )

    parser.add_argument(
        "commands",
        nargs="*",
        metavar="COMMAND",
        help="commands to execute in the order given",
    )


class Main(base.BaseMain):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args)
        self._repo: Optional[git.Repo] = None
        self._crates: Optional[List[Crate]] = None

    def _get_start(self) -> str:
        start = self.args.start
        if start is None:
            raise error.UsageError("missing START")
        elif start == "0":
            start = ""
        return str(start)

    def get_start(self) -> str:
        start = self._get_start()
        if (
            start
            and self.args.allow_missing_start
            and not self.branch_exists(start)
        ):
            start = ""
        return start

    def get_start_branch_name(self) -> str:
        start = self._get_start()
        if start == "":
            raise error.UsageError("START may not be 0 or empty")
        return start

    def get_repo(self) -> git.Repo:
        if self._repo is None:
            self._repo = get_repo(self.args.index)
        return self._repo

    def branch_exists(self, branch: str) -> bool:
        try:
            self.get_repo().commit(branch)
        except git.BadName:
            return False
        return True

    def forget_crates(self) -> None:
        self._crates = None

    def get_crates(self) -> List[Crate]:
        if self._crates is None:
            common.vprint("[calculating crate list]")
            crate_iter = crates_in_range(
                self.get_repo(), self.get_start(), self.args.end
            )
            crates_by_ident = {crate.ident: crate for crate in crate_iter}
            self._crates = sorted(
                crates_by_ident.values(), key=lambda crate: crate.ident
            )
            common.vprint(f"[{len(self._crates)} crates in range]")
        return self._crates

    def get_bundle_path(self) -> Path:
        if self.args.bundle_path:
            path = Path(self.args.bundle_path)
        elif self.args.index:
            path = get_index_path(self.args.index) / INDEX_BUNDLE_NAME
        else:
            raise error.UsageError("missing BUNDLE_PATH")
        # Use .absolute() because git operations change the working directory.
        return path.absolute()

    def get_origin_bundle_path(self) -> Path:
        """Path for repo's remote "origin" URL"""
        url = get_origin_url(self.get_repo())
        parsed = urllib.parse.urlparse(url)
        if len(parsed.scheme) > 1 or parsed.netloc:
            raise error.UsageError(
                "INDEX remote ``origin`` must have ``url`` as a local file"
            )
        else:
            path = Path(url)

        if self.args.bundle_path and (
            path.resolve() != Path(self.args.bundle_path).resolve()
        ):
            raise error.UsageError(
                "BUNDLE_PATH must match ``url`` for INDEX's ``origin`` remote"
            )

        return path

    def get_commands(self) -> List[str]:
        valid_commands = [
            "pull",
            "download",
            "verify",
            "pack",
            "mark",
            "unpack",
            "list",
            "update",
            "export",
            "import",
            "init",
            "init-import",
            "config",
        ]

        commands = [str(c) for c in self.args.commands]
        if commands:
            base.verify_commands(commands, valid_commands)
        else:
            common.iprint("Nothing to do (try --help)")
        return commands

    def cmd_pull(self) -> None:
        self.forget_crates()
        repo = self.get_repo()
        fetch_origin(repo)
        merge_origin_master(repo)

    def cmd_mark(self) -> None:
        self.forget_crates()
        mark(
            self.get_repo(),
            self.args.end,
        )

    def cmd_unpack(self) -> None:
        self.forget_crates()
        unpack(
            self.get_repo(),
            get_crates_root_path(self.args.crates),
            self.get_origin_bundle_path(),
            self.get_archive_path(),
            self.args.keep_going,
        )

    def cmd_list(self) -> None:
        list_crates(self.get_crates())

    def cmd_download(self) -> None:
        download_crates(
            self.downloader,
            self.args.crates_url,
            self.get_crates(),
            get_crates_root_path(self.args.crates),
            self.args.good_paths,
            self.args.bad_paths,
            keep_going=self.args.keep_going,
            assume_ok=self.args.assume_ok,
        )

    def cmd_verify(self) -> None:
        verify_crates(
            self.downloader,
            self.get_crates(),
            get_crates_root_path(self.args.crates),
            self.args.good_paths,
            self.args.bad_paths,
            keep_going=self.args.keep_going,
            assume_ok=self.args.assume_ok,
        )

    def cmd_pack(self) -> None:
        if self.get_crates():
            bundle_path = self.get_bundle_path()
            git_bundle_create(
                self.get_repo(),
                str(bundle_path),
                self.get_start(),
                self.args.end,
            )

            pack(
                self.get_crates(),
                get_crates_root_path(self.args.crates),
                bundle_path,
                self.get_archive_path(),
                self.args.keep_going,
            )
        else:
            common.iprint("No crates to pack")

    def cmd_init(self) -> None:
        index_path = Path(self.args.index)
        prefix_style = PrefixStyle.from_config_str(self.args.prefix_style)
        index_url = self.args.index_url
        parsed = urllib.parse.urlparse(index_url)
        if not parsed.scheme and not parsed.netloc:
            # This is not a URL, but a local path.
            # Relative local directories in Git remotes can cause trouble,
            # because when they are stored in the .git/config file they are
            # interpreted to be relative to the .git/ directory, which changes
            # their meaning.
            index_url = os.path.abspath(index_url)
        init(index_path, index_url, Path(self.args.crates), prefix_style)

    def cmd_init_import(self) -> None:
        index_path = Path(self.args.index)
        prefix_style = PrefixStyle.from_config_str(self.args.prefix_style)
        init_import(index_path, Path(self.args.crates), prefix_style)

    def cmd_config(self) -> None:
        self.forget_crates()
        configure_index(self.get_repo(), self.args.server_url)
        mark(self.get_repo(), self.args.end)

    def _run(self) -> None:
        if not self.args.start:
            self.args.start = "mark"
            self.args.allow_missing_start = True

        crates_root_path = Path(self.args.crates)
        _prevent_mixed_with_case_insensitive(crates_root_path)

        commands = self.get_commands()

        while commands:
            command = commands.pop(0)
            common.iprint(f"{command}...")
            if command in ("update", "export", "import"):
                if command == "update":
                    cmd = "pull download mark"
                elif command == "export":
                    cmd = "pull download pack mark"
                else:
                    cmd = "unpack pull verify mark"
                commands = cmd.split() + commands

            else:
                cmd_func_name = "cmd_{}".format(command.replace("-", "_"))
                getattr(self, cmd_func_name)()
