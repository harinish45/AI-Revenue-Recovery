from typing import Dict, Any
from .llm_provider import BaseLLMProvider, OpenAIProvider, LLMDecision

class DeterministicFallbackProvider(BaseLLMProvider):
    """Final fallback provider that uses rule-based logic when all LLMs fail."""
    def get_decision(self, payment_data: Dict[str, Any], history: Dict[str, Any]) -> LLMDecision:
        code = payment_data.get("failure_code", "")
        if code == "insufficient_funds":
            return LLMDecision(
                decision="PAYMENT_LINK", 
                reason="Customer lacks funds. Offering split payment link.",
                evidence=["Failure code: insufficient_funds"],
                confidence=0.85
            )
        elif code in ["gateway_timeout", "bank_maintenance", "upi_pin_retry_limit", "3ds_authentication_failed"]:
            return LLMDecision(
                decision="RETRY_PAYMENT",
                reason="Transient banking/network issue or authentication retry.",
                evidence=[f"Failure code: {code}"],
                confidence=0.95
            )
        elif code == "mandate_revoked":
            return LLMDecision(
                decision="CUSTOMER_REMINDER",
                reason="Mandate revoked. Needs customer to re-establish mandate.",
                evidence=["Failure code: mandate_revoked"],
                confidence=0.90
            )
        elif code == "invalid_card":
            return LLMDecision(
                decision="HUMAN_REVIEW",
                reason="Invalid card details. Potential fraud or typo. Halting automated retries.",
                evidence=["Failure code: invalid_card"],
                confidence=0.99
            )
        else:
            return LLMDecision(
                decision="HUMAN_REVIEW",
                reason="Unknown failure state. Escalating to human.",
                evidence=[f"Unknown failure code: {code}"],
                confidence=0.50
            )

class LLMProviderChain:
    def __init__(self):
        self.providers = [
            OpenAIProvider(),
            DeterministicFallbackProvider() # MUST remain as final fallback
        ]

    def get_decision(self, payment_data: Dict[str, Any], history: Dict[str, Any]) -> LLMDecision:
        for provider in self.providers:
            try:
                decision = provider.get_decision(payment_data, history)
                if decision is not None:
                    return decision
            except Exception:
                continue
        return DeterministicFallbackProvider().get_decision(payment_data, history)

chain = LLMProviderChain()
