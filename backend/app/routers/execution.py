from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ExecuteRecoveryRequest
from app.services.decision_engine import diagnose_and_strategize
from app.services.policy_engine import check_policies
from app.services.executor import execute_recovery
from app.services.audit_service import log_action
from app.models import RecoveryCase, RecoveryStatus

router = APIRouter()

@router.post("/execute")
def execute(req: ExecuteRecoveryRequest, db: Session = Depends(get_db)):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == req.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    success, msg = diagnose_and_strategize(db, req.case_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
        
    approved, policy_msg = check_policies(db, req.case_id)
    if not approved:
        if policy_msg == "ESCALATE":
            case.status = RecoveryStatus.ESCALATED
            log_action(db, req.case_id, "ESCALATED", {"reason": "Amount exceeds threshold"})
            db.commit()
            return {"status": "escalated", "message": "Case escalated due to amount threshold"}
        raise HTTPException(status_code=403, detail=f"Policy violation: {policy_msg}")
        
    recovered, exec_msg = execute_recovery(db, req.case_id)
    
    return {
        "status": "recovered" if recovered else "nudged",
        "message": exec_msg,
        "case_id": req.case_id
    }
