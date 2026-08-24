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


def choose_intervention(reason_code: str, success_rate: float) -> AgentDecision:
    """Select the safest useful intervention from payment evidence.

    This is intentionally deterministic for the demo. A model can later
    replace this function while keeping the same typed decision contract.
    """
    reason = (reason_code or "").lower()
    if "gateway" in reason or "timeout" in reason:
        return AgentDecision(
            "temporary_gateway_failure", "retry_payment", "low",
            "Transient gateway issue; retry once while the failure is recoverable.",
            0.94, "payment_gateway",
            ["stop after 2 attempts", "escalate if the retry fails"],
        )
    if "insufficient" in reason:
        return AgentDecision(
            "customer_liquidity_issue", "payment_link", "medium",
            "Funds appear unavailable; offer a deferred payment path without repeated retries.",
            0.91, "payment_link",
            ["do not retry the card", "escalate after the payment-link window expires"],
        )
    if "bank" in reason or "invalid" in reason:
        return AgentDecision(
            "bank_or_instrument_rejection", "needs_human_review", "high",
            "The payment instrument was rejected; automated retries could frustrate the customer or increase risk.",
            0.96, "human_review",
            ["never retry automatically", "require human approval for alternate collection"],
        )
    confidence = 0.86 if success_rate >= 40 else 0.72
    return AgentDecision(
        "user_abandonment", "customer_reminder", "low",
        "Checkout appears abandoned; send one gentle reminder and stop if it is ignored.",
        confidence, "customer_message",
        ["send at most one reminder", "do not contact after opt-out"],
    )
