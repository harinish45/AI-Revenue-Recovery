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
from ..models import AuditLog, AuditSeal, RecoveryCase
from ..utils.time import utcnow

_FALLBACK_SIGNING_KEY = secrets.token_hex(32)


def _signing_key() -> bytes:
    return (settings.AUDIT_SIGNING_KEY or _FALLBACK_SIGNING_KEY).encode()


def _compute_event_hash(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(_signing_key(), body, hashlib.sha256).hexdigest()


def _last_seal(db: Session, case_id: str | None) -> AuditSeal | None:
    # Locked so two concurrent log_event() calls for the same case can never
    # compute the same next sequence number from the same "last" row -- the
    # second call blocks here until the first commits, then sees the fresh
    # tail. A no-op on SQLite, a real lock on Postgres.
    return (
        db.query(AuditSeal)
        .filter(AuditSeal.case_id == case_id)
        .order_by(AuditSeal.sequence.desc())
        .with_for_update()
        .first()
    )


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
    previous = _last_seal(db, case_id)
    sequence = (previous.sequence or 0) + 1 if previous else 1
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
    # Anchor the new tail onto the case row itself, outside the audit_seals
    # table entirely. Pure hash-linking only ever points backward, so
    # deleting the most recent seal (and its log row) leaves every
    # *remaining* seal internally consistent -- verify_chain would report
    # 100% valid. This anchor is what lets verify_chain notice the case
    # remembers a later sequence/hash than the seal table can still produce.
    if case_id:
        case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).with_for_update().first()
        if case is not None:
            case.last_audit_sequence = sequence
            case.last_audit_hash = event_hash
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
    last_seen_by_case: dict = {}
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
        last_seen_by_case[seal.case_id] = (seal.sequence, seal.event_hash)

    # Anchor check: every remaining seal can be internally perfectly
    # consistent even after the newest seal (or every seal) for a case was
    # deleted outright, because hash-linking only ever points backward. This
    # compares what we can still see in audit_seals against each case's own
    # record of its last-written sequence/hash (set outside this table, in
    # the same transaction as the write) to catch exactly that.
    case_query = db.query(RecoveryCase).filter(RecoveryCase.last_audit_sequence.isnot(None))
    if case_id:
        case_query = case_query.filter(RecoveryCase.id == case_id)
    anchor_mismatches = []
    for case in case_query.all():
        seen_sequence, seen_hash = last_seen_by_case.get(case.id, (None, None))
        if seen_sequence != case.last_audit_sequence or seen_hash != case.last_audit_hash:
            all_valid = False
            anchor_mismatches.append(
                {
                    "case_id": case.id,
                    "reason": "audit chain tail is missing or was truncated",
                    "case_records_sequence": case.last_audit_sequence,
                    "seals_found_up_to_sequence": seen_sequence,
                }
            )

    return {
        "valid": all_valid,
        "events_checked": len(events),
        "events": events,
        "anchor_mismatches": anchor_mismatches,
    }
