"""
main.py — FastAPI application entry point
------------------------------------------
RecoverAI Backend
Razorpay Hackathon Track 03 — AI Revenue Recovery

API prefix structure:
  /api/demo/*       — Demo control (seed, reset, batch, failure sim)
  /api/dashboard/*  — Live metrics
  /api/cases/*      — Recovery case CRUD
  /api/execution/*  — Recovery execution
  /api/audit/*      — Compliance audit log
  /api/providers/*  — LLM provider status
  /health           — Health check (for startup scripts + monitoring)

Static file serving:
  If frontend/dist/ exists (production build), serves it at root.
  This allows single-process deployment (no separate frontend server).
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routers import dashboard, cases, execution, audit, demo
from .config import settings


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Create DB tables on startup (after test engine override if any)."""
    from .database import engine, Base
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="RecoverAI API",
    description=(
        "AI-powered revenue recovery for Razorpay Test Mode. "
        "Hackathon Track 03 — AI Revenue Recovery.\n\n"
        "**Hybrid AI Architecture:**\n"
        "- AI layer: LLM provider chain (Groq → OpenRouter → Nvidia NIM → OpenAI → Deterministic)\n"
        "- Execution layer: Deterministic policy engine + bounded recovery executor\n"
        "- Razorpay adapter: Test mode only — no real money moved"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS
# Specific origins only. allow_origins=["*"] + allow_credentials=True
# is rejected by browsers — must enumerate trusted origins.
# ---------------------------------------------------------------------------
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(demo.router, prefix="/api/demo", tags=["Demo Control"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(cases.router, prefix="/api/cases", tags=["Recovery Cases"])
app.include_router(execution.router, prefix="/api/execution", tags=["Execution"])
app.include_router(audit.router, prefix="/api/audit", tags=["Compliance Audit"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
def health():
    """
    Health check endpoint.
    Returns LLM provider status, database status, and payment count.
    Used by startup scripts and deployment monitoring.
    """
    # Database check
    try:
        from .database import SessionLocal
        from .models import Payment
        db = SessionLocal()
        payment_count = db.query(Payment).count()
        db.close()
        db_status = "READY"
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "UNHEALTHY",
                "database": f"ERROR: {str(exc)}",
            },
        )

    # LLM provider status
    try:
        from .services.llm_provider_chain import get_provider_chain
        chain = get_provider_chain()
        provider_status = chain.get_provider_status()
        active_providers = chain.get_active_providers()
        primary_provider = active_providers[0] if active_providers else "none"
    except Exception:
        provider_status = []
        primary_provider = "unknown"

    return {
        "status": "OK",
        "service": "RecoverAI Backend",
        "version": "1.0.0",
        "database": db_status,
        "payment_count": payment_count,
        "llm_provider": primary_provider,
        "llm_providers": provider_status,
        "hackathon": "Razorpay Track 03 — AI Revenue Recovery",
        "mode": "SANDBOX — Razorpay Test Mode Only",
    }


# ---------------------------------------------------------------------------
# LLM provider status endpoint
# ---------------------------------------------------------------------------
@app.get("/api/providers", tags=["LLM Providers"])
def provider_status():
    """Return current LLM provider chain status."""
    from .services.llm_provider_chain import get_provider_chain
    chain = get_provider_chain()
    return {
        "providers": chain.get_provider_status(),
        "active": chain.get_active_providers(),
        "priority_order": "groq → openrouter → nvidia_nim → openai → deterministic_fallback",
    }


# ---------------------------------------------------------------------------
# Static frontend serving (production deployment)
# ---------------------------------------------------------------------------
_FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    # Serve frontend static files at root — single deployable unit
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """Serve React SPA — all non-API routes return index.html."""
        index = _FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse({"message": "Frontend not built. Run: cd frontend && npm run build"})

else:
    @app.get("/", tags=["Root"])
    def root():
        return {
            "message": "RecoverAI Backend is running.",
            "docs": "/docs",
            "health": "/health",
            "hackathon": "Razorpay Track 03 — AI Revenue Recovery",
            "note": "Frontend not built. Run: cd frontend && npm run build",
        }
