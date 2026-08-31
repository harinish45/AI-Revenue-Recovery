"""Tamper-evident audit service.

Every event is sealed with an HMAC-SHA256 hash chained to the previous event
for the same case, plus a monotonic sequence number so ordering never depends
on timestamps (which can collide under concurrency).

The seal is keyed with ``AUDIT_SIGNING_KEY`` rather than a plain SHA-256 hash:
without a secret key, anyone with database write access (a leaked app
credential, an operator mistake, an insider) could rewrite audit history and
recompute a fully self-consistent chain, and ``verify_chain`` would report it
as valid. HMAC means forging the chain requires the key, not just the
(public) hashing algorithm. Production deployments must set
``AUDIT_SIGNING_KEY`` explicitly (enforced at startup in main.py); dev/demo
falls back to a random key generated once per process, which still makes the
chain internally verifiable for the lifetime of that process.
"""

import hashlib
import hmac
import json
import secrets
import uuid

from sqlalchemy.orm import Session

from ..config import settings
from ..models import AuditLog, AuditSeal
from ..utils.time import utcnow

_FALLBACK_SIGNING_KEY = secrets.token_hex(32)


def _signing_key() -> bytes:
    return (settings.AUDIT_SIGNING_KEY or _FALLBACK_SIGNING_KEY).encode()


def _compute_event_hash(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(_signing_key(), body, hashlib.sha256).hexdigest()


def _next_sequence(db: Session, case_id: str | None) -> int:
    last = (
        db.query(AuditSeal)
        .filter(AuditSeal.case_id == case_id)
        .order_by(AuditSeal.sequence.desc())
        .first()
    )
    return (last.sequence or 0) + 1 if last else 1


def log_event(
    db: Session,
    case_id: str,
    event_type: str,
    actor: str = "recoverai-agent",
    decision: str = None,
    reason: str = None,
    action: str = None,
    result: str = None,
) -> AuditLog:
    # Flush pending seals first: sessions run with autoflush=False, and without
    # this the sequence/previous queries cannot see events logged moments ago
    # in the same transaction — which would fork the hash chain.
    db.flush()
    # SQLite and PostgreSQL serialize timezone-aware datetimes differently. Store
    # a normalized UTC value so the sealed payload can be reproduced exactly.
    timestamp = utcnow().replace(tzinfo=None)
    event_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
    sequence = _next_sequence(db, case_id)
    previous = (
        db.query(AuditSeal)
        .filter(AuditSeal.case_id == case_id)
        .order_by(AuditSeal.sequence.desc())
        .first()
    )
    payload = {
        "id": event_id,
        "case_id": case_id,
        "event_type": event_type,
        "actor": actor,
        "decision": decision,
        "reason": reason,
        "action": action,
        "result": result,
        "timestamp": timestamp.isoformat(),
        "sequence": sequence,
        "previous_hash": previous.event_hash if previous else None,
    }
    event_hash = _compute_event_hash(payload)
    log = AuditLog(
        id=event_id,
        case_id=case_id,
        event_type=event_type,
        actor=actor,
        decision=decision,
        reason=reason,
        action=action,
        result=result,
        timestamp=timestamp,
    )
    db.add(log)
    db.add(
        AuditSeal(
            audit_id=event_id,
            case_id=case_id,
            sequence=sequence,
            previous_hash=previous.event_hash if previous else None,
            event_hash=event_hash,
            created_at=timestamp,
        )
    )
    return log


def verify_chain(db: Session, case_id: str | None = None) -> dict:
    """Recursively verify the hash chain from the root forward.

    Returns the overall validity plus per-event results so a single tampered
    row invalidates every event after it — not just itself.
    """
    query = db.query(AuditSeal)
    if case_id:
        query = query.filter(AuditSeal.case_id == case_id)
    seals = sorted(query.all(), key=lambda s: (s.case_id or "", s.sequence or 0))

    logs_by_id = {
        log.id: log
        for log in db.query(AuditLog).filter(AuditLog.id.in_([s.audit_id for s in seals])).all()
    }

    events = []
    previous_hash_by_case: dict = {}
    all_valid = True
    for seal in seals:
        log = logs_by_id.get(seal.audit_id)
        expected_previous = previous_hash_by_case.get(seal.case_id)
        if log is None:
            events.append(
                {"audit_id": seal.audit_id, "valid": False, "reason": "audit event missing"}
            )
            all_valid = False
            continue
        payload = {
            "id": log.id,
            "case_id": log.case_id,
            "event_type": log.event_type,
            "actor": log.actor,
            "decision": log.decision,
            "reason": log.reason,
            "action": log.action,
            "result": log.result,
            "timestamp": log.timestamp.isoformat(),
            "sequence": seal.sequence,
            "previous_hash": seal.previous_hash,
        }
        computed = _compute_event_hash(payload)
        hash_ok = computed == seal.event_hash
        link_ok = seal.previous_hash == expected_previous
        valid = hash_ok and link_ok
        if not valid:
            all_valid = False
        events.append(
            {
                "audit_id": seal.audit_id,
                "sequence": seal.sequence,
                "valid": valid,
                "hash_ok": hash_ok,
                "chain_link_ok": link_ok,
            }
        )
        previous_hash_by_case[seal.case_id] = seal.event_hash

    return {"valid": all_valid, "events_checked": len(events), "events": events}
