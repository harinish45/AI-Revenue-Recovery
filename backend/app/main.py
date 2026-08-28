import json
import logging
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
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


def _ensure_sqlite_compatibility():
    """Apply additive fixes for demo databases created by an older checkout."""
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
async def security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started = perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
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
