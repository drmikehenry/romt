from pathlib import Path
import platform
from tempfile import NamedTemporaryFile
import typing as T
import re
import shutil
import sys
import textwrap

import nox
from nox import parametrize
from nox_poetry import Session, session

nox.options.error_on_external_run = True
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["lint", "type_check", "test", "req_check"]


def get_project_version() -> str:
    for line in open("pyproject.toml"):
        # Expected line:
        #   version = "0.6.1"
        m = re.search(
            r"""
                ^
                \s* version \s* = \s*
                "
                ( (\d|\.)+ )
                "
                $
            """,
            line,
            re.VERBOSE,
        )
        if m:
            return T.cast(str, m.group(1))
    raise Exception("could not find `romt` version in `pyproject.toml`")


def get_target_os() -> str:
    if sys.platform.startswith("linux"):
        target_os = "linux"
    elif sys.platform.startswith("darwin"):
        target_os = "darwin"
    elif sys.platform.startswith("win"):
        target_os = "windows"
    else:
        target_os = "unknown"
    return target_os


def get_target_arch() -> str:
    arch = platform.machine().lower()
    if arch == "amd64":
        arch = "x86_64"
    elif arch == "arm64":
        arch = "aarch64"
    return arch


def rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


@session(python=["3.8", "3.9", "3.10", "3.11", "3.12"])
def test(s: Session) -> None:
    s.install(".", "pytest", "pytest-cov")
    s.run(
        "python",
        "-m",
        "pytest",
        "--cov=romt",
        "--cov-report=html",
        "--cov-report=term",
        "tests",
        *s.posargs,
    )


# For some sessions, set `venv_backend="none"` to simply execute scripts within
# the existing Poetry environment. This requires that `nox` is run within
# `poetry shell` or using `poetry run nox ...`.
@session(venv_backend="none")
def fmt(s: Session) -> None:
    s.run("ruff", "check", ".", "--select", "I", "--fix")
    s.run("ruff", "format", ".")


@session(venv_backend="none")
@parametrize(
    "command",
    [
        ["ruff", "check", "."],
        ["ruff", "format", "--check", "."],
    ],
)
def lint(s: Session, command: T.List[str]) -> None:
    s.run(*command)


@session(venv_backend="none")
def lint_fix(s: Session) -> None:
    s.run("ruff", "check", ".", "--fix")


@session(venv_backend="none")
def type_check(s: Session) -> None:
    s.run("mypy", "src", "tests", "noxfile.py")


@session(venv_backend="none")
def req_check(s: Session) -> None:
    expected = s.run_always(
        "poetry",
        "export",
        external=True,
        silent=True,
    )
    actual = open("requirements.txt").read()
    if actual != expected:
        s.error(
            "`requirements.txt` is out-of-date ( nox -s req_fix )",
        )


@session(venv_backend="none")
def req_fix(s: Session) -> None:
    s.run_always(
        "poetry",
        "export",
        "-o",
        "requirements.txt",
        external=True,
        silent=True,
    )


# Note: This `reuse_venv` does not yet have effect due to:
#   https://github.com/wntrblm/nox/issues/488
@session(reuse_venv=False)
def licenses(s: Session) -> None:
    # Generate a unique temporary file name. Poetry cannot write to the temp
    # file directly on Windows, so only use the name and allow Poetry to
    # re-create it.
    with NamedTemporaryFile() as t:
        requirements_path = Path(t.name)

    # Install dependencies without installing the package itself:
    #   https://github.com/cjolowicz/nox-poetry/issues/680
    s.run_always(
        "poetry",
        "export",
        "--without-hashes",
        f"--output={requirements_path}",
        external=True,
    )
    s.install("pip-licenses", "-r", str(requirements_path))
    s.run("pip-licenses", *s.posargs)
    requirements_path.unlink()


@session(venv_backend="none")
def build(s: Session) -> None:
    version = get_project_version()
    target_os = get_target_os()
    target_arch = get_target_arch()
    target_platform = f"{target_arch}-{target_os}"
    if target_os == "windows":
        suffix = ".exe"
    else:
        suffix = ""
    dist_path = Path("dist") / target_platform
    work_path = Path("build") / target_platform
    github_path = Path("dist") / "github"
    dist_exe_path = dist_path / ("romt" + suffix)
    github_exe_path = github_path / f"romt-{version}-{target_platform}{suffix}"

    rmtree(dist_path)
    rmtree(work_path)
    github_path.mkdir(parents=True, exist_ok=True)
    github_exe_path.unlink(missing_ok=True)

    s.run("poetry", "install")
    args = ["pyinstaller"]
    args.append("--onefile")
    args.extend(["--name", "romt"])
    args.extend(["--distpath", str(dist_path)])
    args.extend(["--specpath", str(work_path)])
    args.extend(["--workpath", str(work_path)])
    args.append("--add-data=../../README.rst:romt")
    args.extend(["--log-level", "WARN"])
    args.append("romt-wrapper.py")
    s.run(*args)
    s.log(f"copy {dist_exe_path} -> {github_exe_path}")
    shutil.copy(dist_exe_path, github_exe_path)


@session(venv_backend="none")
def build_linux(s: Session) -> None:
    # Remove any stray container if it exists; use
    # `success_codes` to prevent `nox` failure if the
    # container does not exist and `docker rm` fails.
    s.run("docker", "rm", "romt-build", success_codes=[0, 1], silent=True)
    s.run("docker", "build", ".", "-t", "romt-build")
    s.run(
        "docker",
        "run",
        "-v",
        "./src:/src",
        "--name",
        "romt-build",
        "romt-build",
    )
    s.run("docker", "cp", "romt-build:/dist/.", "dist/")
    s.run("docker", "rm", "romt-build")


@session(venv_backend="none")
def release(s: Session) -> None:
    version = get_project_version()
    tar_path = Path("dist") / f"romt-{version}.tar.gz"
    whl_path = Path("dist") / f"romt-{version}-py3-none-any.whl"
    rmtree(Path("dist"))
    rmtree(Path("build"))
    s.log("NOTE: safe to perform Windows steps now...")
    s.run("poetry", "install")
    # Build the `romt` executable for Linux:
    build_linux(s)
    s.run("poetry", "build")
    s.run("twine", "check", str(tar_path), str(whl_path))
    print(
        textwrap.dedent(
            f"""
        ** Remaining manual steps:

        On Windows machine:
          poetry run nox -s build
        Alternatively, unzip from CI:
          unzip -d dist/ dist-windows-latest.zip

        Tag and push:
          git tag -am 'Release v{version}.' v{version}
          git push; git push --tags

        Upload to PyPI:
          twine upload {tar_path} {whl_path}

        Create Github release for {version} from tree:
          dist/github/
        """
        )
    )
