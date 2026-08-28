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
    DEMO_MODE: bool = False
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    WEBHOOK_SECRET: str = ""
    WEBHOOK_MAX_AGE_SECONDS: int = 300
    APP_ENV: str = "development"
    # Optional shared secret; when set, demo control routes additionally require
    # a matching X-Demo-Token header.
    DEMO_API_TOKEN: str = ""
    WEBHOOK_MAX_BODY_BYTES: int = 262144
    WEBHOOK_ALLOWED_EVENTS: tuple = (
        "payment.failed",
        "payment.captured",
        "payment_link.paid",
        "refund.processed",
    )
    # Retry cooldowns: the first intervention may fire immediately, but every
    # subsequent retry must respect the scheduled window.
    RETRY_COOLDOWN_FIRST_HOURS: float = 4.0
    RETRY_COOLDOWN_HOURS: float = 24.0
    # Case amount and payment amount must agree within this tolerance.
    AMOUNT_TOLERANCE: float = 0.01


    @property
    def demo_controls_enabled(self) -> bool:
        """Demo control-plane routes are safe only outside production."""
        return self.DEMO_MODE and self.APP_ENV.lower() != "production"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
