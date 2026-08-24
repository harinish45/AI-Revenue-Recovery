from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    DATABASE_URL: str = "sqlite:///./recoverai.db"
    CORS_ORIGINS: list[str] = ["null", "http://localhost:5173", "http://localhost:3000"]
    MAX_RETRIES: int = 2
    MAX_AMOUNT: float = 50000.0
    RATE_LIMIT_EXECUTE: str = "20/minute"
    RATE_LIMIT_DEMO: str = "10/minute"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
