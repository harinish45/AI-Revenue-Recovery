from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration for the backend, grouped by concern.

    Every setting is read from the environment (or a local ``.env`` file —
    see ``.env.example`` at the repo root and in ``backend/``). Defaults are
    chosen so the app runs safely out of the box with zero configuration:
    simulated payments, no auth, a per-process audit key. Production
    deployments must override the Security section explicitly, or the app
    refuses to boot — see ``_enforce_production_secrets`` in ``main.py``.
    """

    # ---------------------------------------------------------------- #
    # Environment
    # ---------------------------------------------------------------- #
    # "development" (default) or "production". Gates demo routes and the
    # startup check that requires API_KEYS/AUDIT_SIGNING_KEY to be set.
    APP_ENV: str = "development"

    # ---------------------------------------------------------------- #
    # Database
    # ---------------------------------------------------------------- #
    DATABASE_URL: str = "sqlite:///./recoverai.db"

    # ---------------------------------------------------------------- #
    # CORS
    # ---------------------------------------------------------------- #
    # Origins allowed to call this API from a browser. Empty by default —
    # safe for the same-origin standalone cockpit served at "/", but the
    # React dev server (http://localhost:5173) needs its own origin added
    # here, e.g. CORS_ORIGINS=["http://localhost:5173"], or its requests
    # will silently fail and the UI will show "Backend offline".
    CORS_ORIGINS: list = []

    # ---------------------------------------------------------------- #
    # Razorpay / payment provider
    # ---------------------------------------------------------------- #
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    # Simulate every provider call instead of hitting the real Razorpay API.
    # True by default so the app is safe and fully demoable with zero keys.
    RAZORPAY_SIMULATE: bool = True

    # ---------------------------------------------------------------- #
    # Recovery policy & safety thresholds — the numbers the policy engine
    # gates every execution against (see services/policy_engine.py).
    # ---------------------------------------------------------------- #
    MAX_RETRIES: int = 2
    MAX_AMOUNT: float = 50000.0
    RECOVERY_COST_PER_ATTEMPT: float = 18.0
    # Payments below this amount are smart-skipped: the intervention would
    # cost more than the expected recovery, so the agent never attempts it.
    SMART_SKIP_MIN_AMOUNT: float = 50.0
    # Retry cooldowns: the first intervention may fire immediately, but every
    # subsequent retry must respect the scheduled window (hours).
    RETRY_COOLDOWN_FIRST_HOURS: float = 4.0
    RETRY_COOLDOWN_HOURS: float = 24.0
    # Case amount and payment amount must agree within this tolerance (INR).
    AMOUNT_TOLERANCE: float = 0.01

    # ---------------------------------------------------------------- #
    # Rate limiting
    # ---------------------------------------------------------------- #
    RATE_LIMIT_EXECUTE: str = "20/minute"
    RATE_LIMIT_DEMO: str = "10/minute"

    # ---------------------------------------------------------------- #
    # Webhooks
    # ---------------------------------------------------------------- #
    WEBHOOK_SECRET: str = ""
    WEBHOOK_MAX_AGE_SECONDS: int = 300
    WEBHOOK_MAX_BODY_BYTES: int = 262144
    WEBHOOK_ALLOWED_EVENTS: tuple = (
        "payment.failed",
        "payment.captured",
        "payment_link.paid",
        "refund.processed",
    )

    # ---------------------------------------------------------------- #
    # Security — API auth and the tamper-evident audit chain
    # ---------------------------------------------------------------- #
    # Core API auth. Each entry is "<key>:<role>", role is "operator"
    # (read + execute) or "readonly" (read only). Empty outside production
    # means "no auth configured yet" and is allowed; empty in production is
    # refused at startup — see main.py's boot check.
    API_KEYS: tuple = ()
    # HMAC key that seals the audit hash chain. Without a real secret,
    # anyone with database write access could recompute a self-consistent
    # chain. Left blank in dev/demo (a random per-process key is generated
    # instead); required when APP_ENV=production.
    AUDIT_SIGNING_KEY: str = ""

    # ---------------------------------------------------------------- #
    # Demo mode — synthetic data, reset, batch, and failure simulation.
    # Off by default and hard-disabled in production regardless of this
    # flag (see Settings.demo_controls_enabled).
    # ---------------------------------------------------------------- #
    DEMO_MODE: bool = False
    # Optional shared secret; when set, demo control routes additionally
    # require a matching X-Demo-Token header.
    DEMO_API_TOKEN: str = ""

    # ---------------------------------------------------------------- #
    # AI-assisted diagnosis (optional) — the deterministic agent in
    # services/recovery_agent.py always runs and always has the final say
    # via the policy engine; this only lets a model *suggest* an action
    # from the same allowlist. Off by default; requires OPENAI_API_KEY too.
    # ---------------------------------------------------------------- #
    AI_DIAGNOSIS_ENABLED: bool = False
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

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
