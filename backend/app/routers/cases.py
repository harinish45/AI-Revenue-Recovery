"""
cases.py — Recovery case endpoints
------------------------------------
GET /api/cases/           — list all cases (with payment data)
GET /api/cases/{case_id}  — case detail including executions
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from ..database import get_db
from ..models import RecoveryCase
from ..schemas import RecoveryCaseOut, RecoveryCaseDetail

router = APIRouter()


@router.get("/", response_model=List[RecoveryCaseOut])
def get_cases(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(200, ge=1, le=500, description="Max records to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
):
    """
    List recovery cases, newest first.

    Optional filter:
      ?status=OPEN|RECOVERED|ESCALATED|NEEDS_HUMAN_REVIEW|HALTED
    """
    query = (
        db.query(RecoveryCase)
        .options(joinedload(RecoveryCase.payment))
        .order_by(RecoveryCase.id.desc())
    )

    if status:
        query = query.filter(RecoveryCase.status == status.upper())

    cases = query.offset(skip).limit(limit).all()
    return cases


@router.get("/{case_id}", response_model=RecoveryCaseDetail)
def get_case(case_id: int, db: Session = Depends(get_db)):
    """
    Return full case detail including execution history.
    """
    case = (
        db.query(RecoveryCase)
        .options(
            joinedload(RecoveryCase.payment),
            joinedload(RecoveryCase.executions),
        )
        .filter(RecoveryCase.id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return case
