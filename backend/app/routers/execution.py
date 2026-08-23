"""
execution.py — Recovery execution endpoint
-------------------------------------------
POST /api/execution/execute — execute recovery for a specific case
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import RecoveryCase
from ..schemas import ExecuteRequest
from ..services.recovery_executor import execute_recovery

router = APIRouter()


@router.post("/execute")
def execute(req: ExecuteRequest, db: Session = Depends(get_db)):
    """
    Execute recovery for a specific case.

    Request:
      { "case_id": 42 }

    Response:
      {
        "status": "RECOVERED" | "HALTED" | "ESCALATED" | "NEEDS_HUMAN_REVIEW" | "OPEN",
        "action": str,
        "result": str,
        "amount_recovered": float,
        "message": str
      }

    Note: The backend policy engine is the final authority.
    The execution may be blocked, halted, or escalated regardless
    of the AI recommendation.
    """
    case = (
        db.query(RecoveryCase)
        .filter(RecoveryCase.id == req.case_id)
        .first()
    )
    if not case:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "CASE_NOT_FOUND",
                    "message": f"Recovery case {req.case_id} not found",
                    "request_id": str(req.case_id),
                }
            },
        )

    result = execute_recovery(db, case)
    return result
