from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    customer_email = Column(String)
    customer_name = Column(String, nullable=True)
    amount = Column(Float)
    status = Column(String)
    failure_code = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    recovery_case = relationship("RecoveryCase", back_populates="payment", uselist=False)

class RecoveryCase(Base):
    __tablename__ = "recovery_cases"
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"))
    status = Column(String, default="OPEN")
    retry_count = Column(Integer, default=0)
    diagnosis = Column(String)
    recommended_action = Column(String)
    risk_level = Column(String, nullable=True)
    
    payment = relationship("Payment", back_populates="recovery_case")
    executions = relationship("Execution", back_populates="case")

class Execution(Base):
    __tablename__ = "executions"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("recovery_cases.id"))
    action_taken = Column(String)
    result = Column(String)
    amount_recovered = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    case = relationship("RecoveryCase", back_populates="executions")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("recovery_cases.id"), nullable=True)
    event_type = Column(String)
    details = Column(JSON)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
