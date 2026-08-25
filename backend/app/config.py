from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_SIMULATE: bool = True
    DATABASE_URL: str = "sqlite:///./recoverai.db"
    CORS_ORIGINS: list = []
    MAX_RETRIES: int = 2
    MAX_AMOUNT: float = 50000.0
    RATE_LIMIT_EXECUTE: str = "20/minute"
    RATE_LIMIT_DEMO: str = "10/minute"
    RECOVERY_COST_PER_ATTEMPT: float = 18.0
    SMART_SKIP_MIN_AMOUNT: float = 50.0
    AI_DIAGNOSIS_ENABLED: bool = False
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    WEBHOOK_SECRET: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
