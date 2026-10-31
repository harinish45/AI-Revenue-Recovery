import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base
from .utils.time import utcnow


class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    payments = relationship("Payment", back_populates="customer")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, ForeignKey("customers.id"))
    amount = Column(Float)
    currency = Column(String, default="INR")
    status = Column(String)  # success, failed, pending, abandoned
    failure_reason = Column(String, nullable=True)
    gateway = Column(String, default="razorpay")
    failure_code = Column(String, nullable=True)
    card_brand = Column(String, nullable=True)
    timestamp = Column(DateTime, default=utcnow)

    customer = relationship("Customer", back_populates="payments")
    recovery_case = relationship("RecoveryCase", back_populates="payment", uselist=False)


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"
    id = Column(String, primary_key=True, default=lambda: f"RC-{uuid.uuid4().hex[:6].upper()}")
    payment_id = Column(String, ForeignKey("payments.id"))
    customer_id = Column(String, ForeignKey("customers.id"))
    customer_name = Column(String)
    amount_at_risk = Column(Float)
    risk_level = Column(String)
    failure_category = Column(String)
    recommended_action = Column(String)
    reason = Column(String)
    evidence = Column(JSON)
    policy_checks = Column(JSON)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=2)
    recovery_status = Column(
        String, default="pending"
    )  # pending, recovered, failed, needs_human_review, blocked
    recovered_amount = Column(Float, default=0.0)
    action_status = Column(String, default="eligible")
    dunning_state = Column(String, default="pending")
    next_retry_at = Column(DateTime, nullable=True)
    recovery_probability = Column(Float, nullable=True)
    churn_risk_score = Column(Float, nullable=True)
    gateway = Column(String, default="razorpay")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    # Chain-tail anchor: mirrors the sequence/hash of this case's most recent
    # audit seal, written in the same transaction as that seal (see
    # audit_service.log_event). A deleted tail seal can't erase this
    # anchor, so verify_chain can detect truncation that pure hash-linking
    # (each seal only points backward) would otherwise miss entirely.
    last_audit_sequence = Column(Integer, nullable=True)
    last_audit_hash = Column(String, nullable=True)

    payment = relationship("Payment", back_populates="recovery_case")
    executions = relationship("Execution", back_populates="case")
    audit_logs = relationship("AuditLog", back_populates="case")
    notifications = relationship("DunningNotification", back_populates="case")


class DunningNotification(Base):
    """Tracks automated notification sequences delivered to customers."""

    __tablename__ = "dunning_notifications"
    id = Column(String, primary_key=True, default=lambda: f"NOTIF-{uuid.uuid4().hex[:6].upper()}")
    case_id = Column(String, ForeignKey("recovery_cases.id"), nullable=False)
    sequence_step = Column(Integer, default=1)
    template_name = Column(String, nullable=False)
    locale = Column(String, default="en")
    channel = Column(String, default="email")
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    content = Column(String, nullable=False)
    status = Column(String, default="sent")
    sent_at = Column(DateTime, default=utcnow)

    case = relationship("RecoveryCase", back_populates="notifications")


class Execution(Base):
    __tablename__ = "executions"
    id = Column(String, primary_key=True, default=lambda: f"EXE-{uuid.uuid4().hex[:6].upper()}")
    case_id = Column(String, ForeignKey("recovery_cases.id"))
    action_taken = Column(String)
    result = Column(String)
    amount_recovered = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=utcnow)

    case = relationship("RecoveryCase", back_populates="executions")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=lambda: f"AUD-{uuid.uuid4().hex[:6].upper()}")
    case_id = Column(String, ForeignKey("recovery_cases.id"), nullable=True)
    event_type = Column(String)
    actor = Column(String, default="recoverai-agent")
    decision = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    action = Column(String, nullable=True)
    result = Column(String, nullable=True)
    timestamp = Column(DateTime, default=utcnow)

    case = relationship("RecoveryCase", back_populates="audit_logs")


class AuditSeal(Base):
    """Tamper-evident hash metadata for each audit event."""

    __tablename__ = "audit_seals"
    audit_id = Column(String, primary_key=True)
    case_id = Column(String, nullable=True)
    sequence = Column(Integer, nullable=True)  # monotonic per-case chain order
    previous_hash = Column(String, nullable=True)
    event_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        # Belt-and-suspenders alongside the row lock taken before every
        # log_event() call: even if two writers ever raced past that lock,
        # the database itself refuses a second seal at the same position in
        # the same case's chain.
        UniqueConstraint("case_id", "sequence", name="uq_audit_seals_case_sequence"),
    )


class DemoFlag(Base):
    __tablename__ = "demo_flags"
    id = Column(Integer, primary_key=True)
    simulate_failure_active = Column(Boolean, default=False)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    key = Column(String, primary_key=True)
    endpoint = Column(String)
    response = Column(JSON)
    created_at = Column(DateTime, default=utcnow)


class WebhookEvent(Base):
    """Unique webhook receipts make provider retries harmless."""

    __tablename__ = "webhook_events"
    event_id = Column(String, primary_key=True)
    received_at = Column(DateTime, default=utcnow)
