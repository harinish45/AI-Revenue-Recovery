from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import RecoveryCase
from app.schemas import RecoveryCaseOut

router = APIRouter()

@router.get("/", response_model=List[RecoveryCaseOut])
def list_cases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    cases = db.query(RecoveryCase).offset(skip).limit(limit).all()
    return cases

@router.get("/{case_id}", response_model=RecoveryCaseOut)
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case
