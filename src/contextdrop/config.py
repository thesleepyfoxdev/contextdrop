
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "contextdrop"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/contextdrop.db"
    FILESYSTEM_ROOT: str = "./data/files"
    STORAGE_PROVIDER: str = "filesystem"  # Options: "minio", "filesystem"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "password123"
    MINIO_BUCKET: str = "contextdrop"
    MINIO_SECURE: bool = False

    MAX_FILE_SIZE_MB: int = 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
