from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Payment, RecoveryCase
from ..schemas import CaseDetailResponse, CaseOut, CasesListResponse
from ..security.auth import require_readonly
from ..services.policy_engine import compliance_score, retry_window

router = APIRouter(dependencies=[Depends(require_readonly)])


@router.get("/cases", response_model=CasesListResponse)
def get_cases(
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    search: Optional[str] = Query(default=None, max_length=100),
    page: int = Query(1, ge=1, le=10000),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
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

    payments_by_id = {
        p.id: p
        for p in db.query(Payment).filter(Payment.id.in_([c.payment_id for c in cases])).all()
    }

    items = []
    for c in cases:
        payment = payments_by_id.get(c.payment_id)
        next_retry_at = None
        if c.recovery_status in {"pending", "failed"} and c.retry_count < c.max_retries:
            next_retry_at = retry_window(c)
        items.append(
            CaseOut(
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
                created_at=c.created_at,
                compliance_score=compliance_score(c.policy_checks),
                next_retry_at=next_retry_at,
            )
        )

    return CasesListResponse(items=items, page=page, limit=limit, total=total)


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
def get_case(
    case_id: str = Path(..., min_length=1, max_length=64, pattern=r"^RC-[A-Za-z0-9_-]+$"),
    db: Session = Depends(get_db),
):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    payment = db.query(Payment).filter(Payment.id == case.payment_id).first()

    next_retry_at = None
    if case.recovery_status in {"pending", "failed"} and case.retry_count < case.max_retries:
        next_retry_at = retry_window(case)

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
        updated_at=case.updated_at,
        compliance_score=compliance_score(case.policy_checks),
        next_retry_at=next_retry_at,
    )
