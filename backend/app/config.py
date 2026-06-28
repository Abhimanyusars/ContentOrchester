"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the content creation system."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "ContentForge"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    cors_origins: str = Field(default="http://localhost:3000")

    # Standalone mode (no Docker/Redis/Postgres — uses SQLite + in-process tasks)
    standalone_mode: bool = True
    sqlite_path: str = "contentforge.db"

    # Ollama (free, local LLM — no API key required)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    ollama_timeout_seconds: float = 120.0

    # Tavily (free tier: 1000 searches/month)
    tavily_api_key: str = Field(default="", description="Tavily API key")
    tavily_max_results: int = 5

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "contentforge"
    postgres_password: str = "contentforge"
    postgres_db: str = "contentforge"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    # JWT auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    @property
    def database_url(self) -> str:
        """Async database connection URL."""
        if self.standalone_mode:
            return f"sqlite+aiosqlite:///{self.sqlite_path}"
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        if self.redis_password:
            return (
                f"redis://:{self.redis_password}@{self.redis_host}:"
                f"{self.redis_port}/{self.redis_db}"
            )
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parsed CORS origins list."""
        try:
            value = self.cors_origins
            if value.startswith("["):
                import json
                parsed = json.loads(value)
                return [str(origin) for origin in parsed]
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        except Exception as exc:
            raise ValueError(f"Invalid CORS origins: {exc}") from exc

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> str:
        """Allow comma-separated or list CORS origins in env."""
        try:
            if isinstance(value, list):
                return ",".join(value)
            return str(value)
        except Exception as exc:
            raise ValueError(f"Invalid CORS origins: {exc}") from exc


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    try:
        return Settings()
    except Exception as exc:
        raise RuntimeError(f"Failed to load settings: {exc}") from exc
