from fastapi import FastAPI
from app.database import engine, Base
from app.routers import dashboard, cases, execution, audit, batch, demo

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="RecoverAI Backend", version="1.0.0")

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])
app.include_router(execution.router, prefix="/api/execution", tags=["Execution"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
app.include_router(batch.router, prefix="/api/batch", tags=["Batch"])
app.include_router(demo.router, prefix="/api/demo", tags=["Demo"])

@app.get("/")
def read_root():
    return {"message": "Welcome to RecoverAI Backend API"}
