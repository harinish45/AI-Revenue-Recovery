"""Bounded decision layer for the revenue-recovery agent.

The agent chooses an intervention, but never bypasses the policy gate or
executes money movement. Its output is deliberately structured so every
decision can be displayed and audited.
"""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class AgentDecision:
    category: str
    action: str
    risk_level: str
    rationale: str
    confidence: float
    channel: str
    stopping_rules: List[str]

    def as_evidence(self, history: Dict[str, Any]) -> Dict[str, Any]:
        return {
            **history,
            "agent": "recoverai-bounded-agent",
            "confidence": self.confidence,
            "channel": self.channel,
            "stopping_rules": self.stopping_rules,
        }


def _confidence(
    base: float, previous_failures: int, total_payments: int, success_rate: float
) -> float:
    """Turn a category's base pattern-match strength into an evidence-weighted score.

    A fixed per-category number would mean two customers with wildly
    different payment histories get identical confidence for the same
    failure text — which is not a judgment a real agent would make. This
    factors in how much history exists (more data, more trust) and whether
    that history is trending toward repeated failure (less trust), and
    clamps to a band the policy engine's 0.70 confidence gate can actually
    discriminate on.
    """
    value = base - min(0.12, previous_failures * 0.02)
    if total_payments == 0:
        value -= 0.03  # first-ever payment: no track record to corroborate the pattern
    elif total_payments >= 5 and success_rate >= 50:
        value += 0.04  # a customer with a healthy payment history backs up the read
    return round(min(0.99, max(0.55, value)), 2)


def choose_intervention(
    reason_code: str,
    success_rate: float,
    previous_failures: int = 0,
    total_payments: int = 0,
) -> AgentDecision:
    """Select the safest useful intervention from payment evidence.

    The category match is deterministic for the demo (a model can later
    replace it behind the same typed decision contract), but confidence is
    computed from the customer's actual payment history via `_confidence`,
    not a hardcoded number — it is a real function of the evidence.
    """
    reason = (reason_code or "").lower()
    if "gateway" in reason or "timeout" in reason:
        return AgentDecision(
            "temporary_gateway_failure",
            "retry_payment",
            "low",
            "Transient gateway issue; retry once while the failure is recoverable.",
            _confidence(0.94, previous_failures, total_payments, success_rate),
            "payment_gateway",
            ["stop after 2 attempts", "escalate if the retry fails"],
        )
    if "insufficient" in reason:
        return AgentDecision(
            "customer_liquidity_issue",
            "payment_link",
            "medium",
            "Funds appear unavailable; offer a deferred payment path without repeated retries.",
            _confidence(0.91, previous_failures, total_payments, success_rate),
            "payment_link",
            ["do not retry the card", "escalate after the payment-link window expires"],
        )
    if "bank" in reason:
        return AgentDecision(
            "bank_rejection",
            "needs_human_review",
            "high",
            "Payment instrument rejected; automated retries risk frustrating the customer.",
            _confidence(0.96, previous_failures, total_payments, success_rate),
            "human_review",
            ["never retry automatically", "require human approval for alternate collection"],
        )
    if "invalid" in reason:
        return AgentDecision(
            "invalid_instrument",
            "needs_human_review",
            "high",
            "Invalid payment details; automated retries risk frustrating the customer.",
            _confidence(0.96, previous_failures, total_payments, success_rate),
            "human_review",
            ["never retry automatically", "require human approval for alternate collection"],
        )
    return AgentDecision(
        "user_abandonment",
        "customer_reminder",
        "low",
        "Checkout appears abandoned; send one gentle reminder and stop if it is ignored.",
        _confidence(0.80, previous_failures, total_payments, success_rate),
        "customer_message",
        ["send at most one reminder", "do not contact after opt-out"],
    )
