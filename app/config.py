from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal


class Settings(BaseSettings):
    # --- App identity ---
    app_name: str = "ExamAI Agent"
    app_version: str = "0.1.0"

    # --- Environment ---
    env: Literal["development", "staging", "production"] = "development"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1024, le=65535)

    # --- Logging ---
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "console"

    # --- API Keys ---
    openai_api_key: str = Field(default="")
    serper_api_key: str = Field(default="")

    # --- LangSmith tracing ---
    langchain_tracing_v2: str = "false"
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_api_key: str = ""
    langchain_project: str = "examai-agent"

    # --- Agent settings ---
    agent_timeout_seconds: int = Field(default=30, ge=5, le=120)
    max_retries: int = Field(default=3, ge=1, le=10)
    max_search_results: int = Field(default=5, ge=1, le=20)

    # --- Vector store ---
    chroma_persist_dir: str = "./data/chroma"

    # --- Redis cache ---
    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = Field(default=3600, ge=60)

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def debug(self) -> bool:
        return self.env == "development"

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }


settings = Settings()
