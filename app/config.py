# app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Literal


class Settings(BaseSettings):
    """
    All application configuration lives here.
    Values are read from environment variables or .env file.
    Pydantic validates every value at startup — if something is wrong,
    the app refuses to start rather than failing silently later.
    This is called "fail fast" — a core principle in production systems.
    """

    # --- App identity ---
    app_name: str = "ExamAI Agent"
    app_version: str = "0.1.0"

    # --- Environment ---
    # Literal["development", "staging", "production"] means Pydantic will
    # reject any other value. You can't accidentally set ENV=prodcution (typo).
    env: Literal["development", "staging", "production"] = "development"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1024, le=65535)
    # ge = greater than or equal, le = less than or equal
    # Port must be between 1024 and 65535 — ports below 1024 need root access

    # --- Logging ---
    # In development you want human-readable logs.
    # In production you want JSON logs (machine-readable, shippable to Datadog).
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "console"

    # --- API Keys ---
    # default="" means the app starts without them (useful for Day 2/3 testing)
    # Later we'll add validators that enforce these are set in production
    openai_api_key: str = Field(default="")
    serper_api_key: str = Field(default="")

    # --- Agent settings ---
    # How many seconds before we give up on an agent call
    agent_timeout_seconds: int = Field(default=30, ge=5, le=120)
    # How many times to retry a failed API call before giving up
    max_retries: int = Field(default=3, ge=1, le=10)
    # Maximum number of search results to fetch per query
    max_search_results: int = Field(default=5, ge=1, le=20)

    # --- Vector store ---
    chroma_persist_dir: str = "./data/chroma"

    # --- Redis cache ---
    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = Field(default=3600, ge=60)
    # ttl = time to live. After this many seconds, cached answers expire.
    # 3600 = 1 hour. We don't want stale exam answers cached forever.

    @field_validator("openai_api_key")
    @classmethod
    def warn_if_openai_key_missing(cls, v):
        # In Python, an empty string is falsy — "if not v" catches it
        if not v:
            # We warn but don't crash — allows running without key in early dev
            import warnings
            warnings.warn(
                "OPENAI_API_KEY is not set. Agent calls will fail.",
                UserWarning,
                stacklevel=2
            )
        return v

    # Computed properties — derived from other settings, not from .env
    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def debug(self) -> bool:
        # Debug mode is only on in development
        return self.env == "development"

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        # "extra = ignore" means unknown .env variables are silently ignored
        # We want this now that config is comprehensive
        "extra": "ignore"
    }


# Single instance — created once at startup, reused everywhere
# This pattern is called a "singleton"
settings = Settings()
