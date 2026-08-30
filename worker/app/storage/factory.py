from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import StorageProvider


@lru_cache
def get_storage_provider() -> StorageProvider:
    settings = get_settings()
    if settings.appwrite_configured:
        from app.db.client import get_appwrite_client
        from app.storage.appwrite_storage import AppwriteStorageProvider
        from appwrite.services.storage import Storage

        return AppwriteStorageProvider(
            Storage(get_appwrite_client()), settings.appwrite_endpoint, settings.appwrite_project_id
        )
    from app.storage.local_disk import LocalDiskStorageProvider
    return LocalDiskStorageProvider(settings.local_storage_dir)
