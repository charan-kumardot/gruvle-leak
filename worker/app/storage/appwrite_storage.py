from __future__ import annotations

import io
import secrets
import time

from appwrite.input_file import InputFile
from appwrite.services.storage import Storage

from app.storage.base import StorageProvider


class AppwriteStorageProvider(StorageProvider):
    """
    Wraps Appwrite Storage. Buckets are created with `fileSecurity=True` and
    no public read permission (see scripts/provision_appwrite.py) — every
    file is private by default and only reachable via a permission-scoped
    document reference plus this provider's signed URL.
    """

    def __init__(self, storage: Storage, endpoint: str, project_id: str):
        self._storage = storage
        self._endpoint = endpoint.rstrip("/")
        self._project_id = project_id

    async def upload(self, *, bucket: str, file_id: str, filename: str, content: bytes, content_type: str) -> str:
        resolved_id = file_id or f"{int(time.time())}{secrets.token_hex(6)}"
        result = self._storage.create_file(
            bucket_id=bucket,
            file_id=resolved_id,
            file=InputFile.from_bytes(content, filename=filename),
        )
        # appwrite==23's SDK returns a `File` model object here, not a plain
        # dict (unlike the raw REST API) — handle both shapes defensively.
        if isinstance(result, dict):
            return result["$id"]
        return result.id

    async def download(self, *, bucket: str, file_id: str) -> bytes:
        data = self._storage.get_file_download(bucket_id=bucket, file_id=file_id)
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        buf = io.BytesIO()
        for chunk in data:
            buf.write(chunk)
        return buf.getvalue()

    async def delete(self, *, bucket: str, file_id: str) -> None:
        self._storage.delete_file(bucket_id=bucket, file_id=file_id)

    async def get_signed_url(self, *, bucket: str, file_id: str, expires_seconds: int = 3600) -> str:
        # Appwrite file previews/downloads are authorized per-request via the
        # caller's session/JWT rather than a separate signed-URL token; the
        # web app requests through its own authenticated Appwrite session.
        return f"{self._endpoint}/storage/buckets/{bucket}/files/{file_id}/view?project={self._project_id}"
