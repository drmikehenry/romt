#!/usr/bin/env python

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import git
import toml

import romt.crate

orig_path = Path("orig").absolute()
tmp_path = orig_path / "tmp"
orig_crates_path = orig_path / "crates"
orig_index_path = orig_path / "git" / "crates.io-index"


def make_empty_dir(dir_path: Path) -> None:
    if dir_path.is_dir():
        shutil.rmtree(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)


def add_fake_index(crate: romt.crate.Crate) -> None:
    d = dict(
        name=crate.name,
        vers=crate.version,
        deps=[],
        cksum=crate.hash,
        features={},
        yanked=False,
    )
    json_line = json.dumps(d)
    prefix = crate.prefix(romt.crate.PrefixStyle.LOWER)
    json_path = orig_index_path / prefix / crate.name.lower()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("a") as f:
        f.write(json_line + "\n")
    repo.index.add(str(json_path))
    repo.index.commit(f"Add {crate.name}-{crate.version}")


def add_fake_crate(name: str, version: str) -> None:
    proj_path = tmp_path / name
    if proj_path.is_dir():
        shutil.rmtree(proj_path)
    subprocess.run(["cargo", "new", str(proj_path)])
    toml_path = proj_path / "Cargo.toml"
    toml_data = toml.load(toml_path)
    toml_data["package"]["version"] = version
    with toml_path.open("w") as f:
        toml.dump(toml_data, f)

    subprocess.run(["git", "add", "--all"], cwd=proj_path)
    subprocess.run(
        ["git", "commit", "-m", f"version {version}"], cwd=proj_path
    )
    subprocess.run(["cargo", "package"], cwd=proj_path)
    src_package_path = next(proj_path.glob("target/package/*.crate"))
    print(src_package_path)
    h = hashlib.sha256()
    h.update(src_package_path.read_bytes())
    cksum = h.hexdigest()
    crate = romt.crate.Crate(name, version, cksum)

    prefix_style = romt.crate._crates_config_prefix_style(crates_config)
    rel_path = crate.rel_path(prefix_style)
    crate_path = orig_crates_path / rel_path
    crate_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_package_path, crate_path)
    add_fake_index(crate)


##############################################################################

orig_path.mkdir(exist_ok=True)
make_empty_dir(tmp_path)
make_empty_dir(orig_crates_path)
crates_config = romt.crate._default_crates_config()
romt.crate._write_crates_config(orig_crates_path, crates_config)

make_empty_dir(orig_index_path)
repo = git.Repo.init(str(orig_index_path), initial_branch="master")

config_json = """\
{
  "dl": "https://crates.io/api/v1/crates",
  "api": "https://crates.io/"
}
"""

config_path = orig_index_path / "config.json"
config_path.write_text(config_json)
repo.index.add(str(config_path))
repo.index.commit("Apply config.json adjustments")


add_fake_crate("something", "0.1.0")
add_fake_crate("SomeCrate", "0.1.0")
add_fake_crate("SOON", "0.1.0")
