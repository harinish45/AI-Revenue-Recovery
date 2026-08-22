from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import dashboard, cases, execution, audit, demo

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RecoverAI Backend", description="Autonomous Revenue Recovery Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(demo.router, prefix="/api/demo", tags=["Demo"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])
app.include_router(execution.router, prefix="/api/execution", tags=["Execution"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])

@app.get("/")
def root():
    return {"message": "RecoverAI Backend is running. Visit /docs for API documentation."}
