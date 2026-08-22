from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import datetime
import enum

class PaymentStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    AT_RISK = "at_risk"

class RecoveryStatus(str, enum.Enum):
    OPEN = "open"
    NUDGED = "nudged"
    RECOVERED = "recovered"
    ESCALATED = "escalated"
    HALTED = "halted"

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    razorpay_payment_id = Column(String, unique=True, index=True)
    customer_id = Column(String, index=True)
    customer_email = Column(String)
    customer_phone = Column(String)
    amount = Column(Float)
    currency = Column(String, default="INR")
    status = Column(Enum(PaymentStatus), default=PaymentStatus.FAILED)
    failure_code = Column(String)
    failure_reason = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    recovery_cases = relationship("RecoveryCase", back_populates="payment")

class RecoveryCase(Base):
    __tablename__ = "recovery_cases"
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"))
    status = Column(Enum(RecoveryStatus), default=RecoveryStatus.OPEN)
    retry_count = Column(Integer, default=0)
    root_cause_diagnosis = Column(String)
    intervention_strategy = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    payment = relationship("Payment", back_populates="recovery_cases")
    audit_logs = relationship("AuditLog", back_populates="recovery_case")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    recovery_case_id = Column(Integer, ForeignKey("recovery_cases.id"))
    action = Column(String)
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    recovery_case = relationship("RecoveryCase", back_populates="audit_logs")
