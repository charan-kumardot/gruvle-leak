"""
StorageProvider abstraction. Every uploaded file, extracted artifact, and
generated report goes through this interface so the backing store (local
disk for offline/demo dev, Appwrite Storage in normal operation) is a
config choice, never a code change (spec sections 11, 50).
"""
from __future__ import annotations

import abc


class StorageProvider(abc.ABC):
    @abc.abstractmethod
    async def upload(self, *, bucket: str, file_id: str, filename: str, content: bytes, content_type: str) -> str:
        """Returns the storage file id."""

    @abc.abstractmethod
    async def download(self, *, bucket: str, file_id: str) -> bytes:
        ...

    @abc.abstractmethod
    async def delete(self, *, bucket: str, file_id: str) -> None:
        ...

    @abc.abstractmethod
    async def get_signed_url(self, *, bucket: str, file_id: str, expires_seconds: int = 3600) -> str:
        """A private, time-limited URL. Files are never made publicly accessible."""
