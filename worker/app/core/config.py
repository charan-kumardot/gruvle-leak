from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    appwrite_endpoint: str = "https://cloud.appwrite.io/v1"
    appwrite_project_id: str = ""
    appwrite_api_key: str = ""
    appwrite_database_id: str = "gruvle_leak"

    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    resend_api_key: str = ""

    local_storage_dir: str = "./local_storage"
    demo_mode_fallback: bool = True

    worker_api_internal_token: str = "dev-local-only-change-in-prod"

    # Comma-separated list of origins allowed to call this API — the
    # deployed Next.js app's origin(s) in production, localhost in dev.
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:3001"

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def appwrite_configured(self) -> bool:
        return bool(self.appwrite_project_id and self.appwrite_api_key)

    @property
    def any_ai_provider_configured(self) -> bool:
        return bool(self.gemini_api_key or self.groq_api_key or self.openrouter_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
