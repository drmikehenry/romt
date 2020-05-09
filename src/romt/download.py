#!/usr/bin/env python3
# coding=utf-8

import io
from pathlib import Path
from typing import BinaryIO

import requests

from romt import common
from romt import error
from romt import integrity
from romt import signature


class Downloader:
    def __init__(self) -> None:
        self._session = requests.Session()
        self.sig_verifier = signature.Verifier()
        self._warn_signature = False

    def set_warn_signature(self, warn_signature: bool) -> None:
        self._warn_signature = warn_signature

    def download_fileobj(self, url: str, fileobj: BinaryIO) -> None:
        try:
            response = self._session.get(url, stream=True)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=4096):
                fileobj.write(chunk)
        except requests.exceptions.RequestException as e:
            raise error.DownloadError(url, e)

    def get(self, url: str) -> bytes:
        data = io.BytesIO()
        self.download_fileobj(url, data)
        return data.getvalue()

    def get_text(self, url: str) -> str:
        return self.get(url).decode("utf-8")

    def _download(self, url: str, dest_path: Path) -> None:
        common.make_dirs_for(dest_path)
        try:
            with open(dest_path, "wb") as f:
                self.download_fileobj(url, f)
        except error.DownloadError:
            if dest_path.is_file():
                dest_path.unlink()
            raise

    def download(self, url: str, dest_path: Path) -> None:
        if dest_path.is_file():
            dest_path.unlink()
        tmp_dest_path = common.tmp_path_for(dest_path)
        self._download(url, tmp_dest_path)
        tmp_dest_path.rename(dest_path)

    def download_cached(
        self, dest_url: str, dest_path: Path, *, cached: bool = True
    ) -> None:
        if cached and dest_path.is_file():
            common.vprint("[cached file] {}".format(dest_path))
        else:
            common.vprint("[downloading] {}".format(dest_path))
            self.download(dest_url, dest_path)

    def sig_verify(self, path: Path, sig_path: Path) -> None:
        try:
            self.sig_verifier.verify(path, sig_path)
        except (error.MissingFileError, error.IntegrityError):
            if self._warn_signature:
                common.eprint("Warning: Signature failure for {}".format(path))
            else:
                raise

    def verify_hash(self, path: Path, hash: str) -> None:
        """
        Raises:
            MissingFileError - path doesn't exist
            IntegrityError - path exists with bad hash
        """
        common.vprint("[verify] {}".format(path))
        integrity.verify_hash(path, hash)

    def verify(self, path: Path, *, with_sig: bool = False) -> None:
        """
        Raises:
            MissingFileError - path or associated sha256path doesn't exist
            IntegrityError - paths exists with bad hash
        """
        hash_path = integrity.path_append_hash_suffix(path)
        common.vprint("[verify] {}".format(path))
        integrity.verify(path, hash_path)
        if with_sig:
            sig_path = signature.path_append_sig_suffix(path)
            self.sig_verify(path, sig_path)

    def download_verify_hash(
        self,
        dest_url: str,
        dest_path: Path,
        hash: str,
        *,
        cached: bool = True,
        assume_ok: bool = False
    ) -> None:
        if cached:
            if assume_ok and dest_path.is_file():
                common.vvprint("[assuming OK] {}".format(dest_path))
                return
            try:
                integrity.verify_hash(dest_path, hash)
                common.vprint("[cached file] {}".format(dest_path))
                return
            except (error.MissingFileError, error.IntegrityError):
                pass
        common.vprint("[downloading] {}".format(dest_path))
        self.download(dest_url, dest_path)
        integrity.verify_hash(dest_path, hash)

    def download_verify(
        self,
        dest_url: str,
        dest_path: Path,
        *,
        cached: bool = True,
        assume_ok: bool = False,
        with_sig: bool = False
    ) -> None:
        hash_path = integrity.path_append_hash_suffix(dest_path)
        sig_path = signature.path_append_sig_suffix(dest_path)
        if cached:
            if (
                assume_ok
                and dest_path.is_file()
                and hash_path.is_file()
                and (not with_sig or sig_path.is_file())
            ):
                common.vvprint("[assuming OK] {}".format(dest_path))
                return
            try:
                integrity.verify(dest_path, hash_path)
                if with_sig:
                    self.sig_verify(dest_path, sig_path)
                common.vprint("[cached file] {}".format(dest_path))
                return
            except (error.MissingFileError, error.IntegrityError):
                pass
        common.vprint("[downloading] {}".format(dest_path))
        # Download the (small) hash and signature files first.
        hash_url = integrity.append_hash_suffix(dest_url)
        self.download(hash_url, hash_path)
        if with_sig:
            sig_url = signature.append_sig_suffix(dest_url)
            self.download(sig_url, sig_path)

        # If dest_path exists and has the correct hash, bypass the downloading
        # step to save download time.
        download_required = True
        if dest_path.is_file():
            try:
                integrity.verify(dest_path, hash_path)
                download_required = False
            except (error.MissingFileError, error.IntegrityError):
                pass
        if download_required:
            self.download(dest_url, dest_path)
            integrity.verify(dest_path, hash_path)

        if with_sig:
            self.sig_verify(dest_path, sig_path)
