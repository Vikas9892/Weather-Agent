from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # LLM API Keys & Model selection
    LLM_MODEL: str = "gpt-4o-mini"  # Supports openai/gpt-4o-mini, gemini/gemini-2.0-flash, xai/grok-beta
    LLM_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    XAI_API_KEY: Optional[str] = None
    GROK_API_KEY: Optional[str] = None

    # Weather Providers API Keys
    OPENWEATHER_API_KEY: Optional[str] = None
    WEATHERAPI_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
