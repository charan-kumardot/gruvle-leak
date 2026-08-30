"""
Appwrite server client — used only by the worker service, which holds the
privileged API key. The Next.js frontend never touches this; it uses the
Appwrite Web SDK with per-user sessions instead.
"""
from __future__ import annotations

from functools import lru_cache

from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.services.storage import Storage
from appwrite.services.users import Users

from app.core.config import get_settings


@lru_cache
def get_appwrite_client() -> Client:
    settings = get_settings()
    client = Client()
    client.set_endpoint(settings.appwrite_endpoint)
    client.set_project(settings.appwrite_project_id)
    client.set_key(settings.appwrite_api_key)
    return client


def get_databases() -> Databases:
    return Databases(get_appwrite_client())


def get_storage() -> Storage:
    return Storage(get_appwrite_client())


def get_users() -> Users:
    return Users(get_appwrite_client())
