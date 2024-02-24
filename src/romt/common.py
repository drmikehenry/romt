import datetime
import os
import platform
import re
import stat
import tarfile
from contextlib import contextmanager
from pathlib import Path
from typing import (
    IO,
    Any,
    Generator,
    Iterable,
    List,
    NoReturn,
    Optional,
    Tuple,
)

import romt.error

is_windows = platform.system() == "Windows"


VERBOSITY_ERROR = 0
VERBOSITY_INFO = 1
VERBOSITY_VERBOSE = 2
VERBOSITY_VVERBOSE = 3
_max_verbosity = VERBOSITY_INFO


def get_max_verbosity() -> int:
    return _max_verbosity


def set_max_verbosity(max_verbosity: int) -> None:
    global _max_verbosity
    _max_verbosity = max_verbosity


def _print_verbosity(verbosity: int, *args: Any, **kwargs: Any) -> None:
    if verbosity <= _max_verbosity:
        print(*args, flush=True, **kwargs)


def vvprint(*args: Any, **kwargs: Any) -> None:
    _print_verbosity(VERBOSITY_VVERBOSE, *args, **kwargs)


def vprint(*args: Any, **kwargs: Any) -> None:
    _print_verbosity(VERBOSITY_VERBOSE, *args, **kwargs)


def iprint(*args: Any, **kwargs: Any) -> None:
    _print_verbosity(VERBOSITY_INFO, *args, **kwargs)


def eprint(*args: Any, **kwargs: Any) -> None:
    _print_verbosity(VERBOSITY_ERROR, *args, **kwargs)


def abort(*args: Any, **kwargs: Any) -> NoReturn:
    eprint(*args, **kwargs)
    raise romt.error.AbortError()


def is_date(date: str) -> bool:
    return re.match(r"\d\d\d\d-\d\d-\d\d$", date) is not None


def is_version(version: str) -> bool:
    return re.match(r"\d+\.\d+\.\d+$", version) is not None


def version_sort_key(version: str) -> Tuple[int, ...]:
    return tuple(int(v) for v in version.split("."))


def reverse_sorted_versions(versions: List[str]) -> List[str]:
    return sorted(versions, key=version_sort_key, reverse=True)


def path_append(path: Path, suffix: str) -> Path:
    return path.with_name(path.name + suffix)


def tmp_path_for(path: Path) -> Path:
    return path.with_name("." + path.name + ".tmp")


def path_modified_today(path: Path) -> bool:
    if path.is_file():
        path_mtime = path.stat().st_mtime
        path_mdate = datetime.datetime.fromtimestamp(path_mtime).date()
        today_date = datetime.datetime.now().date()
        modified_today = path_mdate == today_date
    else:
        modified_today = False
    return modified_today


def get_umask() -> int:
    umask = os.umask(0)
    os.umask(umask)
    return umask


def is_executable(path: Path) -> bool:
    return os.access(str(path), os.X_OK)


def chmod_executable(path: Path) -> None:
    x_bits = (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) & ~get_umask()
    os.chmod(str(path), path.stat().st_mode | x_bits)


def gen_dirs(parent: Path) -> Generator[Path, None, None]:
    """generate Path for each dir in parent."""
    for candidate in parent.glob("*"):
        if candidate.is_dir():
            yield candidate


def reversed_date_dir_names(parent: Path) -> List[str]:
    """list of yyyy-mm-dd dirnames in parent (newest to oldest)."""
    dirs = sorted(
        (d.name for d in gen_dirs(parent) if is_date(d.name)),
        reverse=True,
    )
    return dirs


def open_optional(path: str, mode: str) -> Optional[IO[Any]]:
    return open(path, mode) if path else None


def close_optional(f: Optional[IO[Any]]) -> None:
    if f:
        f.close()


def make_dirs_for(path: Path) -> None:
    parent = path.parent
    if not parent.is_dir():
        parent.mkdir(parents=True)


def log(log_file: Optional[IO[Any]], message: Any) -> None:
    if log_file is not None:
        log_file.write(f"{message}\n")
        log_file.flush()


def split_word(item: str) -> List[str]:
    """split item into list of words at commas or runs of whitespace.

    Retains any duplicates and empty strings.
    """
    return [part for part in re.split(r"(?:,|\s+)", item)]


def split_flatten_words(words: Iterable[str]) -> List[str]:
    """split_word(each_word in words) into flattened, deduped list."""
    dedup = set()
    result = []
    for w in words:
        for part in split_word(w):
            if part not in dedup:
                dedup.add(part)
                result.append(part)
    return result


def split_flatten_normalize_words(words: Iterable[str]) -> List[str]:
    """split_flatten_words(), remove dups and empty, sort."""
    norm_words = {w for w in split_flatten_words(words) if w}
    return sorted(norm_words)


def normalize_patterns(patterns: Iterable[str]) -> List[str]:
    """split, flatten, remove dups and empty, reduce "*", sort."""
    norm_patterns = split_flatten_normalize_words(patterns)
    if "*" in norm_patterns:
        return ["*"]
    return norm_patterns


@contextmanager
def tar_context(
    archive_path: Path, mode: str
) -> Generator[tarfile.TarFile, None, None]:
    """mode is "r" (read) or "w" (write)."""
    writing = mode == "w"
    if archive_path.name.endswith(".gz"):
        mode += ":gz"

    if writing:
        if archive_path.exists():
            archive_path.unlink()
        tmp_archive_path = tmp_path_for(archive_path)
        tar_f = tarfile.open(str(tmp_archive_path), mode)
        try:
            yield tar_f
        except (Exception, KeyboardInterrupt):
            tar_f.close()
            if tmp_archive_path.is_file():
                tmp_archive_path.unlink()
            raise
        tar_f.close()
        tmp_archive_path.rename(archive_path)
    else:
        tar_f = tarfile.open(str(archive_path), mode)
        tar_f.extraction_filter = tarfile.data_filter
        yield tar_f
        tar_f.close()
