"""Centralised application settings via pydantic-settings.

All environment variables are read on import and validated up-front.
Using `pydantic-settings` gives us:
- type-safe parsing (booleans, ints, urls, paths)
- `.env` file support out of the box
- clear errors when a required variable is missing
- a single source of truth for every env var the app touches.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    # e.g. sqlite:///data/expenses.db   (local dev)
    #      postgresql+psycopg2://user:pass@postgres:5432/budget  (docker)
    database_url: str = "sqlite:///data/expenses.db"

    # ------------------------------------------------------------------
    # Ollama LLM
    # ------------------------------------------------------------------
    ollama_base_url: str = "http://localhost:11434"

    # ------------------------------------------------------------------
    # Reflex / runtime
    # ------------------------------------------------------------------
    uploaded_files_dir: str = "data/uploaded_files"


settings = Settings()
