from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models import PaymentStatus, RecoveryStatus

class PaymentBase(BaseModel):
    razorpay_payment_id: str
    customer_id: str
    amount: float
    status: PaymentStatus
    failure_code: Optional[str] = None

class PaymentOut(PaymentBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class RecoveryCaseBase(BaseModel):
    payment_id: int
    status: RecoveryStatus
    retry_count: int
    root_cause_diagnosis: Optional[str] = None
    intervention_strategy: Optional[str] = None

class RecoveryCaseOut(RecoveryCaseBase):
    id: int
    created_at: datetime
    payment: Optional[PaymentOut] = None
    class Config:
        from_attributes = True

class AuditLogOut(BaseModel):
    id: int
    recovery_case_id: int
    action: str
    details: Dict[str, Any]
    timestamp: datetime
    class Config:
        from_attributes = True

class DashboardSummary(BaseModel):
    total_at_risk: float
    total_recovered: float
    open_cases: int
    escalated_cases: int
    recovery_rate: float

class BatchProcessRequest(BaseModel):
    limit: Optional[int] = 100

class ExecuteRecoveryRequest(BaseModel):
    case_id: int
