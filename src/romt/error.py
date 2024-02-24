from typing import Optional


class Error(Exception):
    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def __str__(self) -> str:
        return f"error: {self.message}"


class UsageError(Error):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class AbortError(Error):
    def __init__(self, message: str = "") -> None:
        if message:
            super().__init__(f"Aborting: {message}")
        else:
            super().__init__("Aborting")


class IntegrityError(Error):
    def __init__(
        self,
        name: str,
        *,
        actual_hash: Optional[str] = None,
        expected_hash: Optional[str] = None,
        sig_name: Optional[str] = None,
    ) -> None:
        if actual_hash and expected_hash:
            message = "Bad hash for {} (got {}, expected {})".format(
                name,
                actual_hash,
                expected_hash,
            )
        elif sig_name:
            message = "Signature failure for {} using signature {}".format(
                name, sig_name
            )
        else:
            message = f"Integrity failure for {name}"
        super().__init__(message)
        self.name = name
        self.actual_hash = actual_hash
        self.expected_hash = expected_hash
        self.sig_name = sig_name


class MissingFileError(Error):
    def __init__(self, name: str) -> None:
        super().__init__(f"missing file {name}")
        self.name = name


class MissingDirectoryError(Error):
    def __init__(self, name: str) -> None:
        super().__init__(f"missing directory {name}")
        self.name = name


class DownloadError(Error):
    def __init__(self, name: str, exception: Exception) -> None:
        super().__init__(
            "failed to download {}; exception details {!r}".format(
                name, exception
            )
        )
        self.name = name
        self.exception = exception


class UnexpectedArchiveMemberError(Error):
    def __init__(self, name: str) -> None:
        super().__init__(f"unexpected archive member {name}")
        self.name = name


class GitError(Error):
    def __init__(self, message: str) -> None:
        super().__init__(f"Git error: {message}")
        self.message = message
