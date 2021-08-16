#!/usr/bin/env python3
# coding=utf-8

import functools
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    BinaryIO,
    Callable,
)

import httpx
import trio

from romt import common
from romt import error
from romt import integrity
from romt import signature


class Downloader:
    def __init__(self, num_jobs: int) -> None:
        self._client = httpx.AsyncClient()
        self.sig_verifier = signature.Verifier()
        self._warn_signature = False
        self.num_jobs = num_jobs

    def set_warn_signature(self, warn_signature: bool) -> None:
        self._warn_signature = warn_signature

    async def adownload_fileobj(self, url: str, fileobj: BinaryIO) -> None:
        try:
            async with self._client.stream("GET", url) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=16384):
                    fileobj.write(chunk)
        except httpx.HTTPError as e:
            raise error.DownloadError(url, e)

    def download_fileobj(self, url: str, fileobj: BinaryIO) -> None:
        self.run_job(self.adownload_fileobj, url, fileobj)

    async def _adownload(self, url: str, dest_path: Path) -> None:
        common.make_dirs_for(dest_path)
        try:
            with dest_path.open("wb") as f:
                await self.adownload_fileobj(url, f)
        except error.DownloadError:
            if dest_path.is_file():
                dest_path.unlink()
            raise

    async def adownload(self, url: str, dest_path: Path) -> None:
        if dest_path.is_file():
            dest_path.unlink()
        tmp_dest_path = common.tmp_path_for(dest_path)
        await self._adownload(url, tmp_dest_path)
        tmp_dest_path.rename(dest_path)

    def download(self, url: str, dest_path: Path) -> None:
        self.run_job(self.adownload, url, dest_path)

    async def adownload_cached(
        self, dest_url: str, dest_path: Path, *, cached: bool = True
    ) -> None:
        if cached and dest_path.is_file():
            common.vprint("[cached file] {}".format(dest_path))
        else:
            common.vprint("[downloading] {}".format(dest_path))
            await self.adownload(dest_url, dest_path)

    def download_cached(
        self, dest_url: str, dest_path: Path, *, cached: bool = True
    ) -> None:
        self.run_job(self.adownload_cached, dest_url, dest_path, cached=cached)

    def _sig_verify(self, path: Path, sig_path: Path) -> None:
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
            self._sig_verify(path, sig_path)

    async def adownload_verify_hash(
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
        await self.adownload(dest_url, dest_path)
        integrity.verify_hash(dest_path, hash)

    def download_verify_hash(
        self,
        dest_url: str,
        dest_path: Path,
        hash: str,
        *,
        cached: bool = True,
        assume_ok: bool = False
    ) -> None:
        self.run_job(
            self.adownload_verify_hash,
            dest_url,
            dest_path,
            hash,
            cached=cached,
            assume_ok=assume_ok,
        )

    async def adownload_verify(
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
                    self._sig_verify(dest_path, sig_path)
                common.vprint("[cached file] {}".format(dest_path))
                return
            except (error.MissingFileError, error.IntegrityError):
                pass
        common.vprint("[downloading] {}".format(dest_path))
        # Download the (small) hash and signature files first.
        hash_url = integrity.append_hash_suffix(dest_url)
        await self.adownload(hash_url, hash_path)
        if with_sig:
            sig_url = signature.append_sig_suffix(dest_url)
            await self.adownload(sig_url, sig_path)

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
            await self.adownload(dest_url, dest_path)
            integrity.verify(dest_path, hash_path)

        if with_sig:
            self._sig_verify(dest_path, sig_path)

    def download_verify(
        self,
        dest_url: str,
        dest_path: Path,
        *,
        cached: bool = True,
        assume_ok: bool = False,
        with_sig: bool = False
    ) -> None:
        self.run_job(
            self.adownload_verify,
            dest_url,
            dest_path,
            cached=cached,
            assume_ok=assume_ok,
            with_sig=with_sig,
        )

    def run_job(
        self, job: Callable[..., Awaitable[None]], *args: Any, **kwargs: Any
    ) -> None:
        trio.run(functools.partial(job, **kwargs), *args)

    def new_limiter(self) -> trio.CapacityLimiter:
        return trio.CapacityLimiter(self.num_jobs)

    def close(self) -> None:
        self.run_job(self._client.aclose)
