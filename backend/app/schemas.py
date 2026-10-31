from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Languages the voice agent is allowed to record (BCP-47 primary subtags).
VOICE_LANGUAGE_ALLOWLIST = {"en", "hi", "ta", "te", "kn", "mr", "bn", "gu", "ml", "pa"}


class DashboardSummary(BaseModel):
    total_revenue: float
    revenue_at_risk: float
    recovered_amount: float
    recovery_rate: float
    total_transactions: int
    failed_payments: int
    open_cases: int = 0
    awaiting_payment_cases: int = 0
    recovery_attempts: int
    successful_recoveries: int
    failed_recoveries: int
    escalated_cases: int
    recovery_cost_per_attempt: float = 18.0
    recovered_mrr: Optional[float] = None
    active_dunning_cases: Optional[int] = None


class RetryAttemptWinRate(BaseModel):
    attempts: int
    recovered: int
    win_rate: float


class RecoveryAnalyticsOut(BaseModel):
    recovered_mrr: float
    active_dunning_cases: int
    dunning_cases_by_stage: Dict[str, int]
    win_rate_by_retry_attempt: Dict[str, RetryAttemptWinRate]
    churn_risk_distribution: Dict[str, int]
    gateway_breakdown: Dict[str, Dict[str, Any]]
    net_revenue_saved: float
    average_recovery_time_hours: float = 18.5


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
    compliance_score: float = 0.0
    next_retry_at: Optional[datetime] = None
    dunning_state: Optional[str] = None
    recovery_probability: Optional[float] = None
    churn_risk_score: Optional[float] = None
    gateway: Optional[str] = "razorpay"

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
    compliance_score: float = 0.0
    next_retry_at: Optional[datetime] = None
    dunning_state: Optional[str] = None
    recovery_probability: Optional[float] = None
    churn_risk_score: Optional[float] = None
    gateway: Optional[str] = "razorpay"

    model_config = ConfigDict(from_attributes=True)


class ExecuteRequest(BaseModel):
    case_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^RC-[A-Za-z0-9_-]+$",
    )


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
    event_hash: Optional[str] = None
    previous_hash: Optional[str] = None
    sequence: Optional[int] = None

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
    batch_id: str = ""
    total_cases: int
    attempted: int
    successful: int
    awaiting: int = 0
    failed: int
    escalated: int
    amount_at_risk: float
    amount_recovered: float
    recovery_rate: float
    skipped: int = 0
    errored: int = 0
    estimated_cost: float = 0.0
    net_recovered: float = 0.0


class AuditSealVerifyResponse(BaseModel):
    audit_id: str
    chain_verified: bool
    event_hash: str
    previous_hash: Optional[str] = None
    case_id: Optional[str] = None


class AuditChainVerifyResponse(BaseModel):
    valid: bool
    events_checked: int
    events: list
    anchor_mismatches: list = []


class WebhookResponse(BaseModel):
    accepted: bool
    event_id: str
    message: str


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
    language: Optional[str] = None
    confidence: Optional[float] = None
    consent_confirmed: Optional[bool] = None

    @field_validator("transcript")
    @classmethod
    def _bound_transcript(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and len(value) > 2000:
            raise ValueError("Transcript exceeds the 2000 character limit")
        return value

    @field_validator("intent")
    @classmethod
    def _bound_intent(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and len(value) > 200:
            raise ValueError("Intent exceeds the 200 character limit")
        return value

    @field_validator("language")
    @classmethod
    def _allowlist_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        primary_subtag = value.split("-")[0].lower()
        if primary_subtag not in VOICE_LANGUAGE_ALLOWLIST:
            raise ValueError("Unsupported language code")
        return value

    @field_validator("confidence")
    @classmethod
    def _bound_confidence(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return value


class VoiceEventResponse(BaseModel):
    audit_event_id: str
    case_id: str
    event_type: str


class ChurnScoreOut(BaseModel):
    recovery_probability: float
    churn_risk_score: float
    risk_tier: str
    expected_recovery_mrr: float
    recommended_strategy: str
    key_factors: List[str]


class DunningStateOut(BaseModel):
    case_id: str
    current_state: str
    failure_category: Optional[str] = None
    next_retry_at: Optional[datetime] = None
    retry_count: int
    max_retries: int
    recovery_probability: Optional[float] = None
    churn_risk_score: Optional[float] = None
    is_terminal: bool


class DunningTransitionRequest(BaseModel):
    target_state: str
    reason: str


class NotificationSendRequest(BaseModel):
    template: str
    sequence_step: int = 1
    locale: Optional[str] = "en"
    channel: Optional[str] = "email"


class NotificationPreviewRequest(BaseModel):
    template: str
    locale: str = "en"
    context: Dict[str, Any] = {}


class DunningNotificationOut(BaseModel):
    id: str
    case_id: str
    sequence_step: int
    template_name: str
    locale: str
    channel: str
    recipient: str
    subject: str
    content: str
    status: str
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)
