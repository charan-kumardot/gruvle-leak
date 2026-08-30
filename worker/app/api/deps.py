"""
Shared FastAPI dependencies. The worker is called only by the Next.js
server (never a browser directly — see docs/ARCHITECTURE.md), so it trusts
requests carrying the shared internal token over trusting request origin
alone. The Next.js side is responsible for having already verified the
caller's Appwrite session and their membership in the business/team named
in the request body before it ever calls the worker.
"""
from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.config import get_settings


def require_internal_token(x_internal_token: str = Header(default="")) -> None:
    settings = get_settings()
    if not settings.worker_api_internal_token or x_internal_token != settings.worker_api_internal_token:
        raise HTTPException(status_code=401, detail="Missing or invalid internal token.")
