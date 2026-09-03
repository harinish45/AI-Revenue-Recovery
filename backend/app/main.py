import json
import logging
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import inspect, text

from .config import settings
from .database import Base, engine
from .middleware.error_handler import (
    http_exception_handler,
    rate_limit_exceeded_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from .middleware.rate_limit import limiter
from .routers import audit, batch, cases, dashboard, demo, execution, health, voice, webhooks


def _resolve_standalone_html_path() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "RecoverAI-standalone.html",
        Path(__file__).resolve().parent.parent / "RecoverAI-standalone.html",
        Path.cwd() / "RecoverAI-standalone.html",
        Path.cwd().parent / "RecoverAI-standalone.html",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


STANDALONE_HTML_PATH = _resolve_standalone_html_path()


def _enforce_production_secrets():
    """Refuse to boot in production without the secrets that make the core
    security controls meaningful, instead of silently running an open API or
    a forgeable audit chain."""
    if not settings.is_production:
        return
    missing = []
    if not settings.api_keys_by_role:
        missing.append("API_KEYS")
    if not settings.AUDIT_SIGNING_KEY:
        missing.append("AUDIT_SIGNING_KEY")
    # Without this, webhooks.py's own guard only rejects unsigned payloads
    # when RAZORPAY_SIMULATE is false -- a production deploy that leaves
    # RAZORPAY_SIMULATE=true (or flips it later) would otherwise boot fine
    # and accept unauthenticated "payment confirmed" webhook events.
    if not settings.WEBHOOK_SECRET:
        missing.append("WEBHOOK_SECRET")
    if missing:
        raise RuntimeError(
            "APP_ENV=production requires the following settings to be configured: "
            + ", ".join(missing)
        )


def _ensure_sqlite_compatibility():
    """Apply additive fixes for demo databases created by an older checkout.

    SQLite never runs the Alembic migrations (the fast demo path only calls
    ``Base.metadata.create_all``, which creates missing *tables* but never
    alters existing ones), so a pre-existing ``recoverai.db`` file needs
    these columns added by hand. The new UNIQUE constraint on
    ``audit_seals(case_id, sequence)`` is deliberately NOT retrofitted here —
    SQLite can't add a constraint to an existing table without rebuilding
    it — a fresh demo database still gets it via ``create_all``.
    """
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    if "audit_seals" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("audit_seals")}
        if "created_at" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE audit_seals ADD COLUMN created_at DATETIME"))
        if "sequence" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE audit_seals ADD COLUMN sequence INTEGER"))
    if "recovery_cases" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("recovery_cases")}
        if "last_audit_sequence" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE recovery_cases ADD COLUMN last_audit_sequence INTEGER")
                )
        if "last_audit_hash" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE recovery_cases ADD COLUMN last_audit_hash VARCHAR")
                )


_enforce_production_secrets()
_ensure_sqlite_compatibility()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="RecoverAI Backend", description="Autonomous Revenue Recovery Agent API")
logger = logging.getLogger("recoverai.request")

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    """Reject an oversized body from Content-Length alone, before it's read.

    Webhooks already enforce their own tighter WEBHOOK_MAX_BODY_BYTES after
    reading the body; this covers every other route too, and rejects before
    Starlette spends memory buffering a payload nobody was ever going to
    accept.
    """
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError:
            declared_size = None
        if declared_size is not None and declared_size > settings.MAX_REQUEST_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"error": {"message": "Request body exceeds the maximum allowed size"}},
            )
    return await call_next(request)


# The standalone cockpit is a single self-contained HTML file with inline
# <script>/<style> and no build step, so 'unsafe-inline' is a deliberate,
# documented tradeoff rather than an oversight -- everything else CSP can
# restrict here (no external origins, no framing, no plugins) still is.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'"
)
# Deny every browser capability this app doesn't use; the voice cockpit's
# speech recognition/synthesis needs the microphone on this same origin.
_PERMISSIONS_POLICY = (
    "microphone=(self), camera=(), geolocation=(), payment=(), usb=(), "
    "interest-cohort=(), browsing-topics=()"
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started = perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = _CSP
    response.headers["Permissions-Policy"] = _PERMISSIONS_POLICY
    # Browsers only ever honor this over a real HTTPS connection, so setting
    # it unconditionally over plain HTTP in local/demo mode is inert, not
    # incorrect -- it activates automatically the moment this is deployed
    # behind TLS, with no code change required.
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            }
        )
    )
    return response


app.include_router(health.router, prefix="/api", tags=["Health"])

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

app.include_router(cases.router, prefix="/api", tags=["Cases"])
app.include_router(execution.router, prefix="/api/execution", tags=["Execution"])
app.include_router(audit.router, prefix="/api", tags=["Audit"])

app.include_router(demo.router, prefix="/api/demo", tags=["Demo"])
app.include_router(voice.router, prefix="/api", tags=["Voice Agent"])
app.include_router(webhooks.router, prefix="/api", tags=["Webhooks"])

# Backward-compatible aliases for earlier hackathon clients. New integrations
# should use the canonical /api/cases, /api/execution, /api/audit and
# /api/demo/recovery-batch routes documented in the root README.
app.include_router(cases.router, prefix="/api/recovery", tags=["Deprecated Compatibility"])
app.include_router(execution.router, prefix="/api/recovery", tags=["Deprecated Compatibility"])
app.include_router(audit.router, prefix="/api/recovery", tags=["Deprecated Compatibility"])
app.include_router(batch.router, prefix="/api/batch", tags=["Deprecated Compatibility"])


# The app IS this page — served same-origin so no CORS setup is ever required to use it.
@app.get("/")
def root():
    return FileResponse(STANDALONE_HTML_PATH)


@app.get("/standalone")
def standalone_demo():
    return RedirectResponse(url="/")
