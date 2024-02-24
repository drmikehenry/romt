import hashlib
import json
import shutil
import typing as T
from pathlib import Path

import git
import pytest
import romt.cli
import romt.crate


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


def make_entry(name: str, version: str, sha256sum: str) -> T.Dict[str, T.Any]:
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
    entry = make_entry(name, version, sha256sum)
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


@pytest.fixture
def upstream_path() -> Path:
    path = Path("fake") / "upstream"
    rmtree(path)
    crates_path = path / "crates"
    mkdir_p(crates_path)
    repo_path = path / "git" / "crates.io-index"
    repo = create_repo(repo_path)
    repo_add_config(repo)
    for name, version in CRATE_VERSIONS:
        add_crate(repo, crates_path, name, version)
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
