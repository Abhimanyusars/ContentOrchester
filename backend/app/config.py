"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
import os
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_files() -> tuple[str, ...] | None:
    """Skip local .env files on Railway so platform env vars always win."""
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_SERVICE_ID"):
        return None
    return (".env", "../.env")


class Settings(BaseSettings):
    """Central configuration for the content creation system."""

    model_config = SettingsConfigDict(
        env_file=_env_files(),
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

    # Groq LLM (cloud — required for all environments)
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_timeout_seconds: float = 120.0

    # Railway / cloud connection strings (override host-based config)
    database_url_override: str | None = Field(default=None, validation_alias="DATABASE_URL")
    database_private_url_override: str | None = Field(
        default=None, validation_alias="DATABASE_PRIVATE_URL"
    )
    redis_url_override: str | None = Field(default=None, validation_alias="REDIS_URL")

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

    @staticmethod
    def _is_valid_connection_url(url: str | None) -> bool:
        """Reject empty or unresolved Railway template variables."""
        if not url or not str(url).strip():
            return False
        cleaned = str(url).strip()
        if "${{" in cleaned or cleaned.startswith("$"):
            return False
        return cleaned.startswith(
            ("postgres://", "postgresql://", "postgresql+asyncpg://", "redis://", "rediss://")
        )

    @staticmethod
    def _normalize_postgres_url(url: str) -> str:
        """Convert Railway/Heroku URLs to asyncpg SQLAlchemy format."""
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def database_url(self) -> str:
        """Async database connection URL."""
        if self.standalone_mode:
            return f"sqlite+aiosqlite:///{self.sqlite_path}"

        for candidate in (self.database_private_url_override, self.database_url_override):
            if self._is_valid_connection_url(candidate):
                return self._normalize_postgres_url(str(candidate).strip())

        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        if self._is_valid_connection_url(self.redis_url_override):
            return str(self.redis_url_override).strip()
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

    @field_validator("standalone_mode", mode="before")
    @classmethod
    def parse_standalone_mode(cls, value: object) -> bool:
        """Accept common bool string formats from Railway env vars."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().strip('"').strip("'").lower()
            if normalized in {"false", "0", "no", "off"}:
                return False
            if normalized in {"true", "1", "yes", "on"}:
                return True
        return bool(value)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> str:
        """Allow comma-separated or list CORS origins in env."""
        try:
            if isinstance(value, list):
                return ",".join(str(v).strip().strip('"').strip("'") for v in value)
            cleaned = str(value).strip()
            if cleaned.startswith("[") and cleaned.endswith("]"):
                import json
                parsed = json.loads(cleaned)
                return ",".join(str(origin).strip().strip('"').strip("'") for origin in parsed)
            return ",".join(
                part.strip().strip('"').strip("'")
                for part in cleaned.split(",")
                if part.strip()
            )
        except Exception as exc:
            raise ValueError(f"Invalid CORS origins: {exc}") from exc


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    try:
        return Settings()
    except Exception as exc:
        raise RuntimeError(f"Failed to load settings: {exc}") from exc
