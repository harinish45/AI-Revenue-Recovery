from ..models import Payment
from .llm_provider_chain import chain

def diagnose_and_recommend(db, payment: Payment) -> tuple:
    payment_data = {
        "id": payment.id,
        "amount": payment.amount,
        "failure_code": payment.failure_code,
        "status": payment.status
    }
    # In a real scenario, history would be fetched from DB
    history = {"previous_success": 5, "previous_failures": 1}
    
    decision = chain.get_decision(payment_data, history)
    
    # Map LLM decision to existing action strings used by recovery_executor
    action_map = {
        "RETRY_PAYMENT": "SEND_RETRY_LINK",
        "PAYMENT_LINK": "OFFER_SPLIT_PAYMENT",
        "CUSTOMER_REMINDER": "SEND_REMINDER_NUDGE",
        "HUMAN_REVIEW": "ESCALATE_TO_HUMAN"
    }
    
    action = action_map.get(decision.decision, "ESCALATE_TO_HUMAN")
    
    return decision.reason, action
