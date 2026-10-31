"""AI Churn Risk & Recovery Scoring Router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import RecoveryCase
from ..schemas import ChurnScoreOut
from ..security.auth import require_readonly
from ..services.churn_scoring import score_case, score_recovery_probability

router = APIRouter()


class EvaluateScoringRequest(BaseModel):
    tenure_months: int = Field(default=6, ge=0)
    decline_code: Optional[str] = None
    failure_reason: Optional[str] = None
    amount: float = Field(default=1000.0, gt=0.0)
    total_payments: int = Field(default=1, ge=0)
    success_rate: float = Field(default=100.0, ge=0.0, le=100.0)
    previous_failures: int = Field(default=0, ge=0)
    attempt_number: int = Field(default=1, ge=1)


@router.get(
    "/cases/{case_id}/churn-risk",
    response_model=ChurnScoreOut,
    dependencies=[Depends(require_readonly)],
)
def get_case_churn_risk(case_id: str, db: Session = Depends(get_db)):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    result = score_case(db, case)
    db.commit()
    return ChurnScoreOut(**result.to_dict())


@router.post(
    "/scoring/evaluate", response_model=ChurnScoreOut, dependencies=[Depends(require_readonly)]
)
def evaluate_scoring(body: EvaluateScoringRequest):
    result = score_recovery_probability(
        tenure_months=body.tenure_months,
        decline_code=body.decline_code,
        failure_reason=body.failure_reason,
        amount=body.amount,
        total_payments=body.total_payments,
        success_rate=body.success_rate,
        previous_failures=body.previous_failures,
        attempt_number=body.attempt_number,
    )
    return ChurnScoreOut(**result.to_dict())
