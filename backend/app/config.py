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

    # API key auth for the core API. Each entry is "<key>:<role>", role is
    # "operator" (read + execute) or "readonly" (read only). Empty outside
    # production means "no auth configured yet" and is allowed; empty in
    # production is refused at startup — see main.py's boot check.
    API_KEYS: tuple = ()
    # HMAC key that seals the audit hash chain. Without a real secret, anyone
    # with database write access could recompute a self-consistent chain, so
    # this is required in production. Left blank in dev/demo, a random
    # per-process key is generated at startup instead.
    AUDIT_SIGNING_KEY: str = ""

    @property
    def demo_controls_enabled(self) -> bool:
        """Demo control-plane routes are safe only outside production."""
        return self.DEMO_MODE and self.APP_ENV.lower() != "production"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def api_keys_by_role(self) -> dict:
        """Parse ``API_KEYS`` entries of the form ``<key>:<role>`` into a map."""
        parsed = {}
        for entry in self.API_KEYS:
            key, _, role = str(entry).partition(":")
            key = key.strip()
            role = role.strip() or "readonly"
            if key:
                parsed[key] = role
        return parsed

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
