"""
schemas.py
----------
Pydantic schemas for all API request/response models.
Uses Pydantic v2 model_config instead of deprecated inner Config class.
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional, Any


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: str
    customer_name: Optional[str] = None
    customer_email: str
    customer_phone: Optional[str] = None
    amount: float
    currency: str = "INR"
    status: str
    failure_code: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

class ExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    action_taken: str
    result: str
    amount_recovered: float
    timestamp: datetime


# ---------------------------------------------------------------------------
# Recovery Case
# ---------------------------------------------------------------------------

class RecoveryCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_id: int
    status: str
    risk_level: str = "MEDIUM"
    diagnosis: Optional[str] = None
    recommended_action: Optional[str] = None
    confidence: float = 0.0
    evidence: List[str] = []
    retry_count: int = 0
    attempt_count: int = 0
    amount_recovered: float = 0.0
    created_at: Optional[datetime] = None
    payment: Optional[PaymentOut] = None


class RecoveryCaseDetail(RecoveryCaseOut):
    """Extended case response including execution history."""
    model_config = ConfigDict(from_attributes=True)

    executions: List[ExecutionOut] = []


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: Optional[int] = None
    event_type: str
    actor: str = "SYSTEM"
    decision: Optional[str] = None
    action: Optional[str] = None
    result_summary: Optional[str] = None
    details: Any = {}
    timestamp: datetime


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardSummary(BaseModel):
    total_payments: int
    total_at_risk: float
    total_recovered: float
    recovery_rate_percent: float
    open_cases: int
    escalated_cases: int
    recovery_attempts: int
    successful_recoveries: int
    failed_recoveries: int


# ---------------------------------------------------------------------------
# Execution request
# ---------------------------------------------------------------------------

class ExecuteRequest(BaseModel):
    case_id: int


# ---------------------------------------------------------------------------
# Batch Recovery Result
# ---------------------------------------------------------------------------

class BatchRecoveryResult(BaseModel):
    total_cases: int
    attempted: int
    successful: int
    failed: int
    escalated: int
    amount_at_risk: float
    amount_recovered: float
    recovery_rate_percent: float


# ---------------------------------------------------------------------------
# Generic OK response
# ---------------------------------------------------------------------------

class OkResponse(BaseModel):
    message: str
    detail: Optional[Any] = None
