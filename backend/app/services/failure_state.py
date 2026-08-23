"""
failure_state.py
----------------
Thread-safe singleton for the failure simulation flag.

When failure_armed is True, the next recovery execution
will produce a controlled gateway failure → NEEDS_HUMAN_REVIEW.
After consumption, failure_armed resets to False.
"""
import threading

_lock = threading.Lock()
_failure_armed: bool = False


def arm_failure() -> None:
    """Arm the failure simulation for the next execution."""
    global _failure_armed
    with _lock:
        _failure_armed = True


def is_armed() -> bool:
    """Check if failure simulation is currently armed."""
    with _lock:
        return _failure_armed


def consume_failure() -> bool:
    """
    Atomically check and consume the failure flag.
    Returns True if the flag was armed (and resets it to False).
    """
    global _failure_armed
    with _lock:
        if _failure_armed:
            _failure_armed = False
            return True
        return False


def reset_failure() -> None:
    """Disarm the failure simulation (e.g., on demo reset)."""
    global _failure_armed
    with _lock:
        _failure_armed = False
