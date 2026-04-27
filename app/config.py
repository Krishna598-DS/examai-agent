# app/config.py

# BaseSettings is a Pydantic class that reads values from environment
# variables (and .env files) automatically.
from pydantic_settings import BaseSettings

# We need to install pydantic-settings separately — it was split from pydantic v2
# Run: pip install pydantic-settings

class Settings(BaseSettings):
    # Each attribute here maps to an environment variable with the same name.
    # If APP_NAME is in your .env, Pydantic reads it here automatically.
    app_name: str = "ExamAI Agent"
    app_version: str = "0.1.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # API keys — Pydantic will raise an error at startup if these are missing
    # That's good! You want to know immediately, not when an agent call fails.
    openai_api_key: str = ""
    serper_api_key: str = ""

    class Config:
        # Tell Pydantic where to find the .env file
        env_file = ".env"
        # Make variable names case-insensitive
        # So both OPENAI_API_KEY and openai_api_key work
        case_sensitive = False

# Create a single instance of Settings.
# Why? Reading .env file is I/O — we don't want to do it on every request.
# We do it once at startup and reuse the same object everywhere.
settings = Settings()
