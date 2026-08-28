"""Optional model-assisted diagnosis with a deterministic safety fallback.

The model may suggest an action; the policy engine remains the authority that
can approve or block execution. Demo mode keeps this disabled by default.
"""

import json
from urllib.request import Request, urlopen

from ..config import settings

ALLOWED_ACTIONS = {"retry_payment", "payment_link", "customer_reminder", "needs_human_review"}


def model_suggest_action(reason: str, amount: float) -> tuple[str | None, str | None]:
    if not settings.AI_DIAGNOSIS_ENABLED or not settings.OPENAI_API_KEY:
        return None, "deterministic_fallback"
    prompt = (
        "You are a revenue-recovery diagnostician. Return JSON only with keys "
        "action and rationale. action must be one of retry_payment, payment_link, "
        "customer_reminder, needs_human_review. Never authorize money movement. "
        f"Failure: {reason}; amount INR: {amount}."
    )
    payload = {
        "model": settings.OPENAI_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You make bounded recovery suggestions."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    request = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=8) as response:
            body = json.loads(response.read().decode())
        content = body["choices"][0]["message"]["content"]
        result = json.loads(content)
        action = result.get("action")
        if action not in ALLOWED_ACTIONS:
            return None, "model_rejected_invalid_action"
        return action, str(result.get("rationale") or "Model-assisted bounded suggestion")
    except Exception:
        return None, "model_unavailable_fallback"
