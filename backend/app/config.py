"""
config.py — Application configuration
--------------------------------------
All settings are loaded from environment variables.
ALL LLM provider keys are optional — the system always works
with zero API keys via deterministic fallback.

Copy .env.example → .env and fill in whichever keys you have.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # -----------------------------------------------------------------------
    # Database
    # -----------------------------------------------------------------------
    DATABASE_URL: str = "sqlite:///./recoverai.db"

    # -----------------------------------------------------------------------
    # Razorpay (optional — simulation used if not provided)
    # -----------------------------------------------------------------------
    RAZORPAY_KEY_ID: str = "dummy_key"
    RAZORPAY_KEY_SECRET: str = "dummy_secret"

    # -----------------------------------------------------------------------
    # LLM Providers (ALL OPTIONAL)
    # Priority order: Groq → OpenRouter → Nvidia NIM → OpenAI → Deterministic
    # -----------------------------------------------------------------------

    # Groq — fast inference, generous free tier
    # Get key: https://console.groq.com/
    GROQ_API_KEY: Optional[str] = None

    # OpenRouter — unified gateway to 100+ models, free tier available
    # Get key: https://openrouter.ai/
    OPENROUTER_API_KEY: Optional[str] = None

    # Nvidia NIM — high-quality open models
    # Get key: https://build.nvidia.com/
    NVIDIA_NIM_API_KEY: Optional[str] = None

    # OpenAI — fallback if above are unavailable
    # Get key: https://platform.openai.com/
    OPENAI_API_KEY: Optional[str] = None

    # -----------------------------------------------------------------------
    # LLM behavior
    # -----------------------------------------------------------------------
    LLM_TIMEOUT_SECONDS: float = 8.0   # Timeout per provider before failover
    LLM_MAX_RETRIES: int = 1           # Retries per provider before moving on

    # -----------------------------------------------------------------------
    # App behavior
    # -----------------------------------------------------------------------
    APP_ENV: str = "development"        # development | production
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
