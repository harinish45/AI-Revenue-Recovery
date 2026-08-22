from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    RAZORPAY_KEY_ID: str = "dummy_key"
    RAZORPAY_KEY_SECRET: str = "dummy_secret"
    DATABASE_URL: str = "sqlite:///./recoverai.db"

    class Config:
        env_file = ".env"

settings = Settings()
