import hashlib
from pathlib import Path
import re
import typing as T

from romt import common
from romt.error import (
    IntegrityError,
    MissingFileError,
)


def hash_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def hash_fileobj(fileobj: T.BinaryIO) -> str:
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


def parse_hash_text(hash_text: str) -> T.Tuple[str, str]:
    # Expected format: text with line in one of two formats:
    #   <sha256>  filename
    #   <sha256> *filename
    # According to the `sha256sum` utility documentation, `filename` was
    # treated as a text file for the first format and a binary file for the
    # second format.  The default behavior for `sha256sum` is unfortunately
    # to assume text files, so it's common for the two-space delimiter to be
    # present even thought the file must be treated as binary on non-Unix
    # systems.  We'll allow both formats, but always generate binary format.
    if hash_text.endswith("\n"):
        hash_text = hash_text[:-1]
    m = re.search(r"^(?P<hash>[0-9a-fA-F]{64}) [ *](?P<name>.*)$", hash_text)
    if not m:
        raise ValueError(f"invalid {hash_text=}")
    return m.group("hash"), m.group("name")


def format_hash_text(hash: str, name: str) -> str:
    return f"{hash} *{name}\n"


def read_hash_file(path: Path) -> T.Tuple[str, str]:
    return parse_hash_text(path.read_text("utf-8"))


_hash_suffix = ".sha256"


def append_hash_suffix(s: str) -> str:
    return s + _hash_suffix


def path_append_hash_suffix(path: Path) -> Path:
    return common.path_append(path, _hash_suffix)


def write_hash_file_for(path: Path, hash: str) -> None:
    path_sha256 = path_append_hash_suffix(path)
    with path_sha256.open("wb") as f:
        hash_text = format_hash_text(hash, path.name)
        f.write(hash_text.encode())


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


def verify(path: Path, hash_path: T.Optional[Path] = None) -> None:
    """
    Raises:
        MissingFileError - either path doesn't exist
        IntegrityError - paths exists with bad hash
    """

    if hash_path is None:
        hash_path = path_append_hash_suffix(path)
    if not hash_path.exists():
        raise MissingFileError(str(hash_path))
    hash, _name = read_hash_file(hash_path)
    verify_hash(path, hash)
