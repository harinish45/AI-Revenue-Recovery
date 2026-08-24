from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict


class DashboardSummary(BaseModel):
    total_revenue: float
    revenue_at_risk: float
    recovered_amount: float
    recovery_rate: float
    total_transactions: int
    failed_payments: int
    recovery_attempts: int
    successful_recoveries: int
    failed_recoveries: int
    escalated_cases: int


class CaseOut(BaseModel):
    id: str
    payment_id: str
    customer_id: str
    customer_name: str
    amount: float
    currency: str
    failure_category: str
    failure_reason: Optional[str]
    risk_level: str
    recommended_action: str
    action_status: str
    recovery_status: str
    recovered_amount: float
    retry_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CasesListResponse(BaseModel):
    items: List[CaseOut]
    page: int
    limit: int
    total: int


class CaseDetailResponse(BaseModel):
    id: str
    payment_id: str
    customer_id: str
    customer_name: str
    amount_at_risk: float
    risk_level: str
    failure_category: str
    failure_reason: Optional[str]
    recommended_action: str
    reason: str
    evidence: Dict[str, Any]
    policy_checks: Dict[str, Any]
    retry_count: int
    max_retries: int
    recovery_status: str
    recovered_amount: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecuteRequest(BaseModel):
    case_id: str


class ExecuteResponse(BaseModel):
    case_id: str
    status: str
    recovered_amount: float
    message: str
    audit_event_id: str


class AuditLogOut(BaseModel):
    id: str
    case_id: Optional[str]
    event_type: str
    actor: str
    decision: Optional[str]
    reason: Optional[str]
    action: Optional[str]
    result: Optional[str]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditListResponse(BaseModel):
    items: List[AuditLogOut]
    page: int
    limit: int
    total: int


class SeedResponse(BaseModel):
    created_records: int
    message: str


class BatchResponse(BaseModel):
    total_cases: int
    attempted: int
    successful: int
    failed: int
    escalated: int
    amount_at_risk: float
    amount_recovered: float
    recovery_rate: float


class SimulateFailureResponse(BaseModel):
    case_id: str
    status: str
    message: str


class ErrorResponse(BaseModel):
    error: Dict[str, str]


class VoiceEventRequest(BaseModel):
    event_type: Literal[
        "voice_call_started",
        "voice_call_ended",
        "voice_promise_captured",
        "voice_dispute_raised",
    ]
    intent: Optional[str] = None
    transcript: Optional[str] = None


class VoiceEventResponse(BaseModel):
    audit_event_id: str
    case_id: str
    event_type: str
