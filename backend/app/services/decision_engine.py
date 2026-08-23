"""
decision_engine.py
------------------
AI decision layer — the "brain" of RecoverAI.

This is the entry point for payment failure analysis.
It calls the LLM provider chain (Groq → OpenRouter → Nvidia NIM → OpenAI →
Deterministic fallback) to produce a structured diagnosis and recommendation.

The flow:
  1. Call LLM provider chain with payment failure context
  2. Log LLM_DIAGNOSIS audit event with case linkage
  3. Return structured DiagnosisResult

IMPORTANT DESIGN PRINCIPLE:
  The LLM ONLY diagnoses and recommends.
  It NEVER directly executes any financial action.
  All recommendations pass through the deterministic policy engine.
"""
from ..models import Payment
from ..services.audit_service import log_event
from ..services.llm_provider_chain import get_provider_chain
from ..services.llm_provider import DiagnosisResult
from sqlalchemy.orm import Session
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def diagnose_and_recommend(
    db: Session,
    payment: Payment,
    case_id: Optional[int] = None,
) -> dict:
    """
    Run AI-powered diagnosis on a failed payment.

    Uses the multi-provider LLM chain:
      Groq → OpenRouter → Nvidia NIM → OpenAI → Deterministic fallback

    If all LLM providers are unavailable or rate-limited,
    the deterministic fallback produces an equivalent result.
    The caller cannot tell the difference — same output schema always.

    Args:
        db:       Database session
        payment:  The failed Payment to diagnose
        case_id:  Associated case ID for audit linkage

    Returns:
        dict with keys:
          diagnosis, decision, reason, evidence, confidence,
          recommended_action, risk_level, provider_used, latency_ms
    """
    chain = get_provider_chain()

    result: DiagnosisResult = chain.diagnose(
        transaction_id=payment.transaction_id,
        failure_code=payment.failure_code or "unknown",
        amount=payment.amount,
        customer_name=payment.customer_name or "Customer",
        customer_email=payment.customer_email,
        retry_count=0,  # Will be updated per case during execution
        payment_status=payment.status,
    )

    # Log the diagnosis to audit trail with proper case linkage
    log_event(
        db,
        case_id=case_id,
        event_type="LLM_DIAGNOSIS",
        details={
            "payment_id": payment.id,
            "transaction_id": payment.transaction_id,
            "failure_code": payment.failure_code,
            "diagnosis": result.diagnosis,
            "recommended_action": result.recommended_action,
            "confidence": result.confidence,
            "risk_level": result.risk_level,
            "provider_used": result.provider_used,
            "latency_ms": result.latency_ms,
        },
        actor=f"AI:{result.provider_used.upper()}",
        decision=result.decision,
        action=result.recommended_action,
        result_summary=(
            f"[{result.provider_used.upper()}] "
            f"Diagnosed: {payment.failure_code} → {result.recommended_action} "
            f"(confidence={result.confidence:.0%})"
        ),
    )

    return {
        "diagnosis": result.diagnosis,
        "decision": result.decision,
        "reason": result.reason,
        "evidence": result.evidence,
        "confidence": result.confidence,
        "recommended_action": result.recommended_action,
        "risk_level": result.risk_level,
        "provider_used": result.provider_used,
        "latency_ms": result.latency_ms,
    }
