from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    RAZORPAY_KEY_ID: str = "dummy_key"
    RAZORPAY_KEY_SECRET: str = "dummy_secret"
    DATABASE_URL: str = "sqlite:///./recoverai.db"
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
