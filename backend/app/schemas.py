from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class PaymentOut(BaseModel):
    id: int
    transaction_id: str
    customer_email: str
    customer_name: Optional[str] = None
    amount: float
    status: str
    failure_code: str
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class RecoveryCaseOut(BaseModel):
    id: int
    payment_id: int
    status: str
    retry_count: int
    diagnosis: Optional[str] = None
    recommended_action: Optional[str] = None
    risk_level: Optional[str] = None
    payment: Optional[PaymentOut] = None
    model_config = ConfigDict(from_attributes=True)

class AuditLogOut(BaseModel):
    id: int
    case_id: Optional[int] = None
    event_type: str
    details: dict
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class DashboardSummary(BaseModel):
    total_payments: int
    total_at_risk: float
    total_recovered: float
    recovery_rate_percent: float
    open_cases: int
    escalated_cases: int

class ExecuteRequest(BaseModel):
    case_id: int

class ExecutionOut(BaseModel):
    id: int
    case_id: int
    action_taken: str
    result: str
    amount_recovered: float
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)
