import filecmp
import hashlib
import json
import os
import shutil
import typing as T
from pathlib import Path

import git
import pytest
import toml

import romt.cli
import romt.crate


def path_append_suffix(path: Path, suffix: str) -> Path:
    return path.with_suffix(path.suffix + suffix)


def rmtree(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)


def mkdir_p(path: Path) -> None:
    if not path.is_dir():
        path.mkdir(parents=True)


def write_file_bytes(path: Path, data: bytes) -> None:
    mkdir_p(path.parent)
    path.write_bytes(data)


def write_file_text(path: Path, text: str) -> None:
    write_file_bytes(path, text.encode())


def append_file_line(path: Path, line: str) -> None:
    mkdir_p(path.parent)
    with open(path, "a") as f:
        f.write(line + "\n")


def walk_files(root: Path) -> T.Generator[Path, None, None]:
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            yield Path(dirpath) / name


def walk_files_rel(root: Path) -> T.Generator[str, None, None]:
    for p in walk_files(root):
        yield str(p.relative_to(root))


def assert_same_files(
    left_root: Path,
    left_files_rel: T.Iterable[str],
    right_root: Path,
    right_files_rel: T.Iterable[str],
) -> None:
    left = set(left_files_rel)
    right = set(right_files_rel)
    common = left & right
    left_only = left - right
    right_only = right - left

    match, mismatch, errors = filecmp.cmpfiles(
        left_root, right_root, common, shallow=False
    )

    print(f"{left_only=}")
    print(f"{right_only=}")
    print(f"{mismatch=}")
    print(f"{errors=}")
    assert not (left_only or right_only or mismatch or errors)


def create_repo(repo_path: Path) -> git.Repo:
    mkdir_p(repo_path)
    repo = git.Repo.init(str(repo_path))
    master = git.Reference(repo, "refs/heads/master")
    repo.head.set_reference(master)
    return repo


def repo_work_path(repo: git.Repo) -> Path:
    working_tree_dir = repo.working_tree_dir
    assert working_tree_dir is not None
    return Path(working_tree_dir)


def repo_add_config(repo: git.Repo) -> None:
    config_path = repo_work_path(repo) / "config.json"
    config = dict(
        dl="https://crates.io/api/v1/crates", api="https://crates.io"
    )
    write_file_text(config_path, json.dumps(config, indent=2))
    repo.index.add(str(config_path))
    repo.index.commit("add `config.json`")


def make_crate_entry(
    name: str, version: str, sha256sum: str
) -> T.Dict[str, T.Any]:
    return dict(
        name=name,
        vers=version,
        deps=[
            # {
            #     "name": "anyhow",
            #     "req": "^1.0.66",
            #     "features": [],
            #     "optional": false,
            #     "default_features": true,
            #     "target": null,
            #     "kind": "normal",
            # }
        ],
        cksum=sha256sum,
        features={},
        yanked=False,
    )


def add_crate(
    repo: git.Repo, crates_path: Path, name: str, version: str
) -> None:
    prefix = romt.crate.crate_prefix_from_name(
        name, romt.crate.PrefixStyle.LOWER
    )
    crate_path = crates_path / prefix / name / f"{name}-{version}.crate"
    crate_data = (crate_path.name + "\n").encode()
    write_file_bytes(crate_path, crate_data)

    work_path = repo_work_path(repo)
    entry_path = work_path / prefix / name
    sha256sum = hashlib.sha256(crate_data).hexdigest()
    entry = make_crate_entry(name, version, sha256sum)
    append_file_line(entry_path, json.dumps(entry))
    repo.index.add(str(entry_path))
    repo.index.commit(f"add `{crate_path.name}`")


CRATE_VERSIONS = [
    ("a", "0.1.0"),
    ("ab", "0.1.0"),
    ("abc", "0.1.0"),
    ("abcd", "0.1.0"),
    ("abcdefgh", "0.1.0"),
]


def make_dist_file(root: Path, url: str) -> str:
    prefix = "https://static.rust-lang.org/"
    assert url.startswith(prefix)
    path = root / url[len(prefix) :]
    data = (path.name + "\n").encode()
    write_file_bytes(path, data)
    sha256sum = hashlib.sha256(data).hexdigest()
    write_file_text(path_append_suffix(path, ".sha256"), sha256sum + "\n")
    return sha256sum


def make_dist(root: Path, manifest: T.Any) -> None:
    if isinstance(manifest, dict):
        url = manifest.get("url")
        if url:
            manifest["hash"] = make_dist_file(root, url)
        xz_url = manifest.get("xz_url")
        if xz_url:
            manifest["xz_hash"] = make_dist_file(root, xz_url)
        for value in manifest.values():
            make_dist(root, value)
    elif isinstance(manifest, list):
        for value in manifest:
            make_dist(root, value)


def write_manifest(manifest_path: Path, manifest_bytes: bytes) -> None:
    manifest_path.write_bytes(manifest_bytes)
    sha256sum = hashlib.sha256(manifest_bytes).hexdigest()
    path_append_suffix(manifest_path, ".sha256").write_text(sha256sum + "\n")


@pytest.fixture
def tests_path(request: pytest.FixtureRequest) -> Path:
    return Path(request.path).parent


@pytest.fixture
def upstream_path(tests_path: Path) -> Path:
    path = Path("fake") / "upstream"
    rmtree(path)

    # Setup upstream crates.
    crates_path = path / "crates"
    mkdir_p(crates_path)
    repo_path = path / "git" / "crates.io-index"
    repo = create_repo(repo_path)
    repo_add_config(repo)
    for name, version in CRATE_VERSIONS:
        add_crate(repo, crates_path, name, version)

    # Setup upstream toolchain.
    manifest = toml.load(tests_path / "channel-rust-1.76.0.toml")
    make_dist(path, manifest)
    manifest_bytes = toml.dumps(manifest).encode()
    dist_path = path / "dist"
    for version in ["1.76.0", "stable"]:
        for p in [dist_path, dist_path / "2024-02-08"]:
            write_manifest(p / f"channel-rust-{version}.toml", manifest_bytes)

    return path


@pytest.fixture
def inet_path() -> Path:
    inet_path = Path("fake") / "inet"
    rmtree(inet_path)
    mkdir_p(inet_path)
    return inet_path


@pytest.fixture
def offline_path() -> Path:
    offline_path = Path("fake") / "offline"
    rmtree(offline_path)
    mkdir_p(offline_path)
    return offline_path


def crate_must_run(root_path: Path, args: T.List[str]) -> None:
    crate_args = [
        "crate",
        "--crates",
        f"{root_path}/crates",
        "--index",
        f"{root_path}/git/crates.io-index",
    ]
    assert romt.cli.run(crate_args + args) == 0


def test_crates(
    upstream_path: Path, inet_path: Path, offline_path: Path
) -> None:
    rmtree(inet_path)
    crates_template = "crates/{lowerprefix}/{crate}/{crate}-{version}.crate"
    archive_path = inet_path / "crates.tar.gz"
    upstream_args = [
        "--crates-url",
        f"{upstream_path}/{crates_template}",
        "--index-url",
        f"{upstream_path}/git/crates.io-index",
        "--archive",
        f"{archive_path}",
    ]

    offline_args = [
        "--crates-url",
        f"{inet_path}/{crates_template}",
        "--index-url",
        f"{inet_path}/git/crates.io-index",
        "--archive",
        f"{archive_path}",
    ]

    crate_must_run(inet_path, upstream_args + ["init"])
    crate_must_run(inet_path, upstream_args + ["export"])

    crate_must_run(offline_path, offline_args + ["init-import"])
    crate_must_run(offline_path, offline_args + ["import"])

    upstream_crates_path = upstream_path / "crates"
    upstream_files_rel = set(walk_files_rel(upstream_crates_path))

    inet_crates_path = inet_path / "crates"
    inet_files_rel = set(walk_files_rel(inet_crates_path))
    inet_files_rel.remove("config.toml")

    assert_same_files(
        upstream_crates_path,
        upstream_files_rel,
        inet_crates_path,
        inet_files_rel,
    )

    offline_crates_path = offline_path / "crates"
    offline_files_rel = set(walk_files_rel(offline_crates_path))
    offline_files_rel.remove("config.toml")

    assert_same_files(
        inet_crates_path,
        inet_files_rel,
        offline_crates_path,
        offline_files_rel,
    )


def test_toolchain(
    upstream_path: Path,
    inet_path: Path,
    offline_path: Path,
) -> None:
    # TODO: write the test.
    assert False
