from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import RecoveryCase, Payment
from ..schemas import CaseOut, CasesListResponse, CaseDetailResponse

router = APIRouter()

@router.get("/cases", response_model=CasesListResponse)
def get_cases(
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(RecoveryCase)
    
    if status:
        query = query.filter(RecoveryCase.recovery_status == status)
    if risk_level:
        query = query.filter(RecoveryCase.risk_level == risk_level)
    if search:
        query = query.filter(RecoveryCase.customer_name.ilike(f"%{search}%"))
        
    total = query.count()
    cases = query.offset((page - 1) * limit).limit(limit).all()
    
    items = []
    for c in cases:
        payment = db.query(Payment).filter(Payment.id == c.payment_id).first()
        items.append(CaseOut(
            id=c.id,
            payment_id=c.payment_id,
            customer_id=c.customer_id,
            customer_name=c.customer_name,
            amount=c.amount_at_risk,
            currency="INR",
            failure_category=c.failure_category,
            failure_reason=payment.failure_reason if payment else None,
            risk_level=c.risk_level,
            recommended_action=c.recommended_action,
            action_status=c.action_status,
            recovery_status=c.recovery_status,
            recovered_amount=c.recovered_amount,
            retry_count=c.retry_count,
            created_at=c.created_at
        ))
        
    return CasesListResponse(items=items, page=page, limit=limit, total=total)

@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    payment = db.query(Payment).filter(Payment.id == case.payment_id).first()
    
    return CaseDetailResponse(
        id=case.id,
        payment_id=case.payment_id,
        customer_id=case.customer_id,
        customer_name=case.customer_name,
        amount_at_risk=case.amount_at_risk,
        risk_level=case.risk_level,
        failure_category=case.failure_category,
        failure_reason=payment.failure_reason if payment else None,
        recommended_action=case.recommended_action,
        reason=case.reason,
        evidence=case.evidence,
        policy_checks=case.policy_checks,
        retry_count=case.retry_count,
        max_retries=case.max_retries,
        recovery_status=case.recovery_status,
        recovered_amount=case.recovered_amount,
        created_at=case.created_at,
        updated_at=case.updated_at
    )
