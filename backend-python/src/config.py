import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SpirandeliEmpire"
    APP_ENV: str = "local"
    APP_KEY: str = "base64:aLc5xmb+c3UNSqUexyQPR1L/85OLK5vV8FATBG/qnfc="
    APP_DEBUG: bool = True
    APP_TIMEZONE: str = "America/Sao_Paulo"
    APP_URL: str = "http://localhost:8080"

    # Database
    DB_CONNECTION: str = "mysql"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3307
    DB_DATABASE: str = "abvos"
    DB_USERNAME: str = "abvos"
    DB_PASSWORD: str = "change-me-db"
    DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = "change-me-redis"

    # Gemini AI
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_MODEL: str = "gemini-3.5-flash"

    # Google Workspace
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = "http://localhost:8080/api/integrations/google/callback"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env.production", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        host = self.DB_HOST
        port = self.DB_PORT
        # Se estiver rodando fora do container Docker e o host for 'db', usa o localhost:3307
        if host == "db" and not os.path.exists("/.dockerenv"):
            host = "127.0.0.1"
            port = 3307
        return f"mysql+aiomysql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{host}:{port}/{self.DB_DATABASE}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
