"""
models.py
---------
SQLAlchemy ORM models for RecoverAI.

Tables:
  payments         - source of truth for failed/abandoned payments
  recovery_cases   - one case per payment, tracks recovery lifecycle
  executions       - every recovery attempt recorded
  audit_logs       - immutable event log for compliance
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    customer_name = Column(String, nullable=True)
    customer_email = Column(String)
    customer_phone = Column(String, nullable=True)
    amount = Column(Float)
    currency = Column(String, default="INR")
    status = Column(String)          # failed | abandoned
    failure_code = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    recovery_case = relationship(
        "RecoveryCase", back_populates="payment", uselist=False
    )


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"))
    status = Column(String, default="OPEN")  # OPEN | IN_PROGRESS | RECOVERED | HALTED | ESCALATED | NEEDS_HUMAN_REVIEW
    risk_level = Column(String, default="MEDIUM")  # LOW | MEDIUM | HIGH

    # Diagnosis fields (structured AI decision output)
    diagnosis = Column(String)
    recommended_action = Column(String)
    confidence = Column(Float, default=0.0)
    evidence = Column(JSON, default=list)

    # Retry tracking
    retry_count = Column(Integer, default=0)   # successful retries
    attempt_count = Column(Integer, default=0)  # total attempts

    # Recovered amount (cumulative)
    amount_recovered = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    payment = relationship("Payment", back_populates="recovery_case")
    executions = relationship("Execution", back_populates="case")


class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("recovery_cases.id"))
    action_taken = Column(String)
    result = Column(String)         # SUCCESS | SIMULATED_SUCCESS | FAILURE | NEEDS_HUMAN_REVIEW
    amount_recovered = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    case = relationship("RecoveryCase", back_populates="executions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("recovery_cases.id"), nullable=True)
    event_type = Column(String)     # LLM_DIAGNOSIS | POLICY_CHECK | EXECUTION_STARTED | RAZORPAY_API_CALL | EXECUTION_COMPLETE | RECOVERY_FAILED | ESCALATED_TO_HUMAN
    actor = Column(String, default="SYSTEM")
    decision = Column(String, nullable=True)
    action = Column(String, nullable=True)
    result_summary = Column(String, nullable=True)
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
