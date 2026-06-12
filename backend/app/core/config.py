from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"

    DATABASE_URL: str = "postgresql+psycopg2://etf:etf@db:5432/etf"

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # AI analysis provider (Phase 13 / CLAUDE.md §7)
    AI_PROVIDER: str = "mock"
    AI_MODEL: str = "claude-opus-4-8"
    ANTHROPIC_API_KEY: str | None = None
    CLAUDE_API_KEY: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
