from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import RecoveryCase
from ..schemas import ExecuteRequest
from ..services.recovery_executor import execute_recovery

router = APIRouter()

@router.post("/execute")
def execute(req: ExecuteRequest, db: Session = Depends(get_db)):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == req.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    result = execute_recovery(db, case)
    return result
