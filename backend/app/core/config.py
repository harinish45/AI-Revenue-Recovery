from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./recoverai.db"
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    MAX_RETRIES: int = 3
    MAX_AMOUNT: float = 100000.0
    ESCALATION_THRESHOLD: float = 50000.0

    class Config:
        env_file = ".env"

settings = Settings()
