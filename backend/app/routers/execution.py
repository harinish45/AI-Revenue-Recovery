from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import RecoveryCase
from ..schemas import ExecuteResponse
from ..services.recovery_executor import execute_recovery

router = APIRouter()

@router.post("/cases/{case_id}/execute", response_model=ExecuteResponse)
def execute_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    result = execute_recovery(db, case)
    return result
