"""Queue boundary kept deliberately small for the Test Mode demo.

Replace ``enqueue_recovery_case`` with Celery, RQ, or a managed queue in a
deployed environment; the policy engine and executor remain unchanged.
"""


def enqueue_recovery_case(case_id: str) -> dict:
    return {"queued": True, "case_id": case_id, "queue": "demo-in-process"}
