"""SpirandeliEmpire OS 3.2 — Global Configuration"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "SpirandeliEmpire OS"
    VERSION: str = "3.2.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", validation_alias="APP_ENV")
    DEBUG: bool = Field(default=True, validation_alias="APP_DEBUG")
    SECRET_KEY: str = Field(default="spirandeli-empire-super-secret-master-key-32b-min", validation_alias="APP_KEY")

    # Authentication & Sessions
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=14, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")
    AUTH_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, validation_alias="AUTH_TOKEN_EXPIRE_MINUTES")
    REGISTRATION_MODE: str = Field(default="public", validation_alias="REGISTRATION_MODE")  # public, disabled, invite_only
    COOKIE_SECURE: bool = Field(default=False, validation_alias="COOKIE_SECURE")

    # Admin Bootstrap (never hardcode passwords in source)
    INITIAL_ADMIN_EMAIL: str = Field(default="spirandelidev@gmail.com", validation_alias="INITIAL_ADMIN_EMAIL")
    INITIAL_ADMIN_PASSWORD: str = Field(default="", validation_alias="INITIAL_ADMIN_PASSWORD")
    INITIAL_ADMIN_NAME: str = Field(
        default="Proprietário / Administrador Principal",
        validation_alias="INITIAL_ADMIN_NAME",
    )

    # Legacy test/dev owner fallback (used only if INITIAL_ADMIN_PASSWORD is not set)
    ADMIN_USERNAME: str = Field(default="owner", validation_alias="ADMIN_USERNAME")
    ADMIN_EMAIL: str = Field(default="owner@spirandeliempire.local", validation_alias="ADMIN_EMAIL")
    ADMIN_PASSWORD: str = Field(default="spirandeli-owner-31", validation_alias="ADMIN_PASSWORD")

    # Master key for Integration Hub / AI Provider secrets encryption (AES-256-GCM + Fernet compat)
    ENCRYPTION_MASTER_KEY: str = Field(
        default="gAamH43t9g86xK_V3zP0N5h3B9lU2mX6qT1y8oQ4z9E=",
        validation_alias="ENCRYPTION_MASTER_KEY"
    )
    ENCRYPTION_KEY_VERSION: str = Field(default="v1", validation_alias="ENCRYPTION_KEY_VERSION")
    PREVIOUS_ENCRYPTION_MASTER_KEY: str = Field(default="", validation_alias="PREVIOUS_ENCRYPTION_MASTER_KEY")

    # Database: Supports PostgreSQL and SQLite
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./spirandeliempire.db",
        validation_alias="DATABASE_URL"
    )

    # Redis URL
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL"
    )

    # Worker dispatch mode
    CELERY_ALWAYS_EAGER: bool = Field(default=False, validation_alias="CELERY_ALWAYS_EAGER")

    # Legacy Gemini env var (preserved for safe migration to Admin BYOK credential)
    GEMINI_API_KEY: str = Field(default="", validation_alias="GEMINI_API_KEY")
    GEMINI_DEFAULT_MODEL: str = Field(default="", validation_alias="GEMINI_DEFAULT_MODEL")
    GEMINI_REASONING_MODEL: str = Field(default="", validation_alias="GEMINI_REASONING_MODEL")

    # Model Discovery Cache TTL (seconds)
    MODEL_CATALOG_CACHE_TTL_SECONDS: int = Field(default=900, validation_alias="MODEL_CATALOG_CACHE_TTL_SECONDS")

    # Storage for deliverables and artifacts
    STORAGE_DIR: Path = Path("/home/spira/spirandeliempire/storage")
    ARTIFACTS_DIR: Path = Path("/home/spira/spirandeliempire/storage/artifacts")
    CHECKPOINTS_DIR: Path = Path("/home/spira/spirandeliempire/storage/checkpoints")

    # Explicit CORS origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:8086",
        "http://localhost:8080",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8086",
        "http://127.0.0.1:8080",
    ]


settings = Settings()

settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
settings.CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
