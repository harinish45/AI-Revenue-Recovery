"""API-key authentication for the core recovery API.

Two roles: ``readonly`` (dashboard/cases/audit reads) and ``operator``
(execution, payment confirmation, voice events — anything that can move a
case toward counted revenue). Webhook and demo-control auth are separate,
existing mechanisms (HMAC signature, ``X-Demo-Token``) and are untouched.

With no ``API_KEYS`` configured outside production this is a no-op, matching
the behavior the public demo and local development already rely on. In
production, ``main.py`` refuses to boot at all unless at least one key is
configured, so the API can never be silently exposed.
"""

import secrets
from typing import Optional

from fastapi import Header, HTTPException, Request

from ..config import settings

_ROLE_RANK = {"readonly": 1, "operator": 2}


def _resolve_role(api_key: Optional[str]) -> Optional[str]:
    if not api_key:
        return None
    for configured_key, role in settings.api_keys_by_role.items():
        if secrets.compare_digest(configured_key, api_key):
            return role
    return None


def require_role(minimum_role: str):
    """FastAPI dependency factory requiring an X-API-Key of at least ``minimum_role``."""

    def _dependency(
        request: Request,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> None:
        if not settings.api_keys_by_role and not settings.is_production:
            return
        role = _resolve_role(x_api_key)
        if role is None:
            raise HTTPException(status_code=401, detail="A valid X-API-Key header is required")
        if _ROLE_RANK.get(role, 0) < _ROLE_RANK.get(minimum_role, 0):
            raise HTTPException(
                status_code=403, detail="This API key does not have sufficient privileges"
            )
        request.state.api_role = role

    return _dependency


require_readonly = require_role("readonly")
require_operator = require_role("operator")
