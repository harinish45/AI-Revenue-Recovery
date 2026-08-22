from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class PaymentOut(BaseModel):
    id: int
    transaction_id: str
    customer_email: str
    amount: float
    status: str
    failure_code: str
    timestamp: datetime
    class Config:
        from_attributes = True

class RecoveryCaseOut(BaseModel):
    id: int
    payment_id: int
    status: str
    retry_count: int
    diagnosis: Optional[str]
    recommended_action: Optional[str]
    payment: Optional[PaymentOut]
    class Config:
        from_attributes = True

class AuditLogOut(BaseModel):
    id: int
    case_id: Optional[int]
    event_type: str
    details: dict
    timestamp: datetime
    class Config:
        from_attributes = True

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
    class Config:
        from_attributes = True
