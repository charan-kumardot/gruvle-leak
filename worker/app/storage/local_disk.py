"""
Local-disk storage — used automatically when Appwrite isn't configured, so
the app still runs end-to-end for local development / demo mode (spec
section 64). Never used in production; AppwriteStorageProvider takes over
the moment APPWRITE_API_KEY is set.
"""
from __future__ import annotations

import os
import secrets
import time

import anyio

from app.storage.base import StorageProvider


class LocalDiskStorageProvider(StorageProvider):
    def __init__(self, root_dir: str):
        self._root = root_dir
        os.makedirs(self._root, exist_ok=True)

    def _path(self, bucket: str, file_id: str) -> str:
        safe_bucket = "".join(c for c in bucket if c.isalnum() or c in "-_")
        safe_id = "".join(c for c in file_id if c.isalnum() or c in "-_.")
        bucket_dir = os.path.join(self._root, safe_bucket)
        os.makedirs(bucket_dir, exist_ok=True)
        return os.path.join(bucket_dir, safe_id)

    async def upload(self, *, bucket: str, file_id: str, filename: str, content: bytes, content_type: str) -> str:
        resolved_id = file_id or f"{int(time.time())}-{secrets.token_hex(8)}"
        path = self._path(bucket, resolved_id)

        def _write():
            with open(path, "wb") as f:
                f.write(content)

        await anyio.to_thread.run_sync(_write)
        return resolved_id

    async def download(self, *, bucket: str, file_id: str) -> bytes:
        path = self._path(bucket, file_id)

        def _read():
            with open(path, "rb") as f:
                return f.read()

        return await anyio.to_thread.run_sync(_read)

    async def delete(self, *, bucket: str, file_id: str) -> None:
        path = self._path(bucket, file_id)
        if os.path.exists(path):
            os.remove(path)

    async def get_signed_url(self, *, bucket: str, file_id: str, expires_seconds: int = 3600) -> str:
        # Dev-only stand-in — never exposed outside localhost, no public route serves this path.
        return f"local://{bucket}/{file_id}?expires_in={expires_seconds}"
