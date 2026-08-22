from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import BatchProcessRequest
from app.services.case_generator import generate_recovery_cases

router = APIRouter()

@router.post("/process")
def process_batch(req: BatchProcessRequest, db: Session = Depends(get_db)):
    cases_created = generate_recovery_cases(db)
    return {"message": f"Batch processed. {cases_created} new recovery cases created."}
