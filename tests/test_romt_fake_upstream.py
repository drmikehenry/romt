import filecmp
import hashlib
import json
import os
import shutil
import textwrap
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


# Create `path` (containing `data`) and `path.sha256`, returning `sha256sum`.
def make_sha256_file_pair(path: Path, data: bytes) -> str:
    write_file_bytes(path, data)
    sha256sum = hashlib.sha256(data).hexdigest()
    write_file_text(path_append_suffix(path, ".sha256"), sha256sum + "\n")
    return sha256sum


# Create `path` and `path.sha256`, returning `sha256sum`.
def make_fake_sha256_file_pair(path: Path) -> str:
    data = (path.name + "\n").encode()
    return make_sha256_file_pair(path, data)


def make_dist_file(root: Path, url: str) -> str:
    prefix = "https://static.rust-lang.org/"
    assert url.startswith(prefix)
    path = root / url[len(prefix) :]
    return make_fake_sha256_file_pair(path)


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
            make_sha256_file_pair(
                p / f"channel-rust-{version}.toml", manifest_bytes
            )

    # Setup upstream `rustup`.
    rustup_path = path / "rustup"
    rustup_toml_path = rustup_path / "release-stable.toml"
    write_file_text(
        rustup_toml_path,
        textwrap.dedent(
            """\
            schema-version = "1"
            version = "1.26.0"
            """
        ),
    )

    target = "x86_64-unknown-linux-gnu"
    version = "1.26.0"
    make_fake_sha256_file_pair(
        rustup_path / "archive" / version / target / "rustup-init"
    )
    make_fake_sha256_file_pair(rustup_path / "dist" / target / "rustup-init")

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
    upstream_crates_path = upstream_path / "crates"
    upstream_files_rel = set(walk_files_rel(upstream_crates_path))

    crates_template = "crates/{lowerprefix}/{crate}/{crate}-{version}.crate"
    archive_path = inet_path / "crates.tar.gz"
    inet_args = [
        "--crates-url",
        f"{upstream_path}/{crates_template}",
        "--index-url",
        f"{upstream_path}/git/crates.io-index",
        "--archive",
        f"{archive_path}",
    ]

    crate_must_run(inet_path, inet_args + ["init"])
    crate_must_run(inet_path, inet_args + ["export"])

    inet_crates_path = inet_path / "crates"
    inet_files_rel = set(walk_files_rel(inet_crates_path))
    inet_files_rel.remove("config.toml")

    assert_same_files(
        upstream_crates_path,
        upstream_files_rel,
        inet_crates_path,
        inet_files_rel,
    )

    offline_args = [
        "--crates-url",
        f"{inet_path}/{crates_template}",
        "--index-url",
        f"{inet_path}/git/crates.io-index",
        "--archive",
        f"{archive_path}",
    ]

    crate_must_run(offline_path, offline_args + ["init-import"])
    crate_must_run(offline_path, offline_args + ["import"])

    offline_crates_path = offline_path / "crates"
    offline_files_rel = set(walk_files_rel(offline_crates_path))
    offline_files_rel.remove("config.toml")

    assert_same_files(
        inet_crates_path,
        inet_files_rel,
        offline_crates_path,
        offline_files_rel,
    )


def toolchain_must_run(root_path: Path, args: T.List[str]) -> None:
    toolchain_args = [
        "toolchain",
        "--dest",
        f"{root_path}/dist",
    ]
    assert romt.cli.run(toolchain_args + args) == 0


toolchain_artifact_names_1_76_0 = set(
    """

    cargo-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    cargo-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    channel-rust-1.76.0.toml
    channel-rust-1.76.0.toml
    channel-rust-1.76.0.toml.sha256
    channel-rust-1.76.0.toml.sha256
    channel-rust-stable.toml
    channel-rust-stable.toml
    channel-rust-stable.toml.sha256
    channel-rust-stable.toml.sha256
    clippy-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    clippy-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    llvm-tools-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    llvm-tools-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    reproducible-artifacts-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    reproducible-artifacts-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    rls-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    rls-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    rust-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    rust-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    rust-analysis-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    rust-analysis-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    rust-analyzer-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    rust-analyzer-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    rust-docs-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    rust-docs-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    rust-src-1.76.0.tar.xz
    rust-src-1.76.0.tar.xz.sha256
    rust-std-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    rust-std-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    rustc-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    rustc-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    rustc-dev-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    rustc-dev-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    rustc-docs-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    rustc-docs-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256
    rustfmt-1.76.0-x86_64-unknown-linux-gnu.tar.xz
    rustfmt-1.76.0-x86_64-unknown-linux-gnu.tar.xz.sha256


""".split()
)


def rel_paths_with_base_names(
    rel_paths: T.Iterable[str], base_names: T.Iterable[str]
) -> T.Generator[str, None, None]:
    names = set(base_names)
    for p in rel_paths:
        if os.path.basename(p) in names:
            yield p


def test_toolchain(
    upstream_path: Path,
    inet_path: Path,
    offline_path: Path,
) -> None:
    upstream_dist_path = upstream_path / "dist"
    upstream_files_rel = set(walk_files_rel(upstream_dist_path))

    inet_dist_path = inet_path / "dist"
    archive_path = inet_path / "toolchain.tar.gz"
    inet_args = [
        "--url",
        str(upstream_dist_path),
        "--archive",
        f"{archive_path}",
        "--no-signature",
    ]

    artifact_names = set(toolchain_artifact_names_1_76_0)

    toolchain_must_run(
        inet_path,
        inet_args + ["-s", "1.76.0", "-t", "linux", "download", "pack"],
    )

    inet_files_rel = set(walk_files_rel(inet_dist_path))

    assert_same_files(
        upstream_dist_path,
        rel_paths_with_base_names(upstream_files_rel, artifact_names),
        inet_dist_path,
        inet_files_rel,
    )

    offline_dist_path = offline_path / "dist"
    offline_args = [
        "--archive",
        f"{archive_path}",
        "--no-signature",
    ]

    toolchain_must_run(
        offline_path,
        offline_args + ["unpack"],
    )

    offline_files_rel = set(walk_files_rel(offline_dist_path))

    assert_same_files(
        inet_dist_path,
        inet_files_rel,
        offline_dist_path,
        offline_files_rel,
    )

    # Now include a `--cross` for a single target.
    cross_target = "x86_64-unknown-linux-musl"
    toolchain_must_run(
        inet_path,
        inet_args
        + ["-s", "1.76.0", "-t", cross_target, "--cross", "download", "pack"],
    )

    artifact_names.update(
        [
            "rust-std-1.76.0-x86_64-unknown-linux-musl.tar.xz",
            "rust-std-1.76.0-x86_64-unknown-linux-musl.tar.xz.sha256",
        ]
    )

    inet_files_rel = set(walk_files_rel(inet_dist_path))

    assert_same_files(
        upstream_dist_path,
        rel_paths_with_base_names(upstream_files_rel, artifact_names),
        inet_dist_path,
        inet_files_rel,
    )

    toolchain_must_run(
        offline_path,
        offline_args + ["unpack"],
    )

    offline_files_rel = set(walk_files_rel(offline_dist_path))

    assert_same_files(
        inet_dist_path,
        inet_files_rel,
        offline_dist_path,
        offline_files_rel,
    )


def rustup_must_run(root_path: Path, args: T.List[str]) -> None:
    toolchain_args = [
        "rustup",
        "--dest",
        f"{root_path}/rustup",
    ]
    assert romt.cli.run(toolchain_args + args) == 0


def test_rustup(
    upstream_path: Path,
    inet_path: Path,
    offline_path: Path,
) -> None:
    upstream_rustup_path = upstream_path / "rustup"
    upstream_files_rel = set(walk_files_rel(upstream_rustup_path))

    inet_rustup_path = inet_path / "rustup"
    archive_path = inet_path / "rustup.tar.gz"
    inet_args = [
        "--url",
        str(upstream_rustup_path),
        "--archive",
        f"{archive_path}",
    ]

    rustup_must_run(
        inet_path,
        inet_args + ["-s", "stable", "-t", "linux", "download", "pack"],
    )

    inet_files_rel = set(walk_files_rel(inet_rustup_path))

    assert_same_files(
        upstream_rustup_path,
        upstream_files_rel,
        inet_rustup_path,
        inet_files_rel,
    )

    offline_rustup_path = offline_path / "rustup"
    offline_args = [
        "--archive",
        f"{archive_path}",
    ]

    rustup_must_run(
        offline_path,
        offline_args + ["unpack"],
    )

    offline_files_rel = set(walk_files_rel(offline_rustup_path))

    assert_same_files(
        inet_rustup_path,
        inet_files_rel,
        offline_rustup_path,
        offline_files_rel,
    )
