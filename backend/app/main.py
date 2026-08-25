from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .config import settings
from .database import Base, engine
from .middleware.error_handler import (
    http_exception_handler,
    rate_limit_exceeded_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from .middleware.rate_limit import limiter
from .routers import audit, batch, cases, dashboard, demo, execution, voice

STANDALONE_HTML_PATH = Path(__file__).resolve().parent.parent.parent / "RecoverAI-standalone.html"

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RecoverAI Backend", description="Autonomous Revenue Recovery Agent API")

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
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

# Recovery routes (Standard Contract)
app.include_router(cases.router, prefix="/api/recovery", tags=["Recovery"])
app.include_router(execution.router, prefix="/api/recovery", tags=["Recovery Execution"])
app.include_router(audit.router, prefix="/api/recovery", tags=["Recovery Audit"])

# Alt Routes (Final Prompt Requirements for guaranteed frontend compatibility)
app.include_router(cases.router, prefix="/api", tags=["Cases Alt"])
app.include_router(execution.router, prefix="/api/execution", tags=["Execution Alt"])
app.include_router(audit.router, prefix="/api", tags=["Audit Alt"])

app.include_router(demo.router, prefix="/api/demo", tags=["Demo"])
app.include_router(batch.router, prefix="/api/batch", tags=["Batch"])
app.include_router(voice.router, prefix="/api", tags=["Voice Agent"])


# The app IS this page — served same-origin so no CORS setup is ever required to use it.
@app.get("/")
def root():
    return FileResponse(STANDALONE_HTML_PATH)


@app.get("/standalone")
def standalone_demo():
    return RedirectResponse(url="/")
