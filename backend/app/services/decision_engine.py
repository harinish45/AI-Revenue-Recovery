from sqlalchemy.orm import Session
from app.models import RecoveryCase, RecoveryStatus, Payment

def diagnose_and_strategize(db: Session, case_id: int):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        return False, "Case not found"
    
    payment = case.payment
    failure_code = payment.failure_code
    
    if failure_code == "insufficient_funds":
        diagnosis = "Customer lacks funds at the moment. Best to offer EMI or a gentle reminder later."
        strategy = "send_whatsapp_emi_offer"
    elif failure_code == "gateway_timeout" or failure_code == "network_error":
        diagnosis = "Technical failure on gateway or network. High chance of success on retry."
        strategy = "send_1_click_retry_link"
    elif failure_code == "user_cancelled":
        diagnosis = "User intentionally dropped off. Might need a discount or assistance."
        strategy = "send_assistance_offer"
    else:
        diagnosis = "Generic failure. Standard retry."
        strategy = "send_generic_retry_link"
        
    case.root_cause_diagnosis = diagnosis
    case.intervention_strategy = strategy
    db.commit()
    return True, "Diagnosed successfully"
