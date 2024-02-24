import hashlib
from pathlib import Path
from typing import BinaryIO, Optional

from romt import common
from romt.error import (
    IntegrityError,
    MissingFileError,
)


def hash_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def hash_fileobj(fileobj: BinaryIO) -> str:
    h = hashlib.sha256()
    while True:
        chunk = fileobj.read(8192)
        if not chunk:
            break
        h.update(chunk)
    return h.hexdigest()


def hash_file(path: Path) -> str:
    with path.open("rb") as f:
        hash = hash_fileobj(f)
    return hash


def parse_hash_text(hash_text: str) -> str:
    # Expected format: text with lines:
    #   <sha256>  filename
    return hash_text.split()[0]


def read_hash_file(path: Path) -> str:
    return parse_hash_text(path.read_text("utf-8"))


_hash_suffix = ".sha256"


def append_hash_suffix(s: str) -> str:
    return s + _hash_suffix


def path_append_hash_suffix(path: Path) -> Path:
    return common.path_append(path, _hash_suffix)


def write_hash_file_for(path: Path) -> None:
    h = hash_file(path)
    path_sha256 = path_append_hash_suffix(path)
    with path_sha256.open("w") as f:
        f.write(f"{h}  {path.name}\n")


def verify_hash(path: Path, expected_hash: str) -> None:
    """
    Raises:
        MissingFileError - path doesn't exist
        IntegrityError - path exists with bad hash
    """

    if not path.exists():
        raise MissingFileError(str(path))
    h = hash_file(path)
    if h != expected_hash:
        raise IntegrityError(
            path.name, actual_hash=h, expected_hash=expected_hash
        )


def verify(path: Path, hash_path: Optional[Path] = None) -> None:
    """
    Raises:
        MissingFileError - either path doesn't exist
        IntegrityError - paths exists with bad hash
    """

    if hash_path is None:
        hash_path = path_append_hash_suffix(path)
    if not hash_path.exists():
        raise MissingFileError(str(hash_path))
    verify_hash(path, read_hash_file(hash_path))
