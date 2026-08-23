"""
llm_provider_chain.py
---------------------
Multi-provider LLM chain with automatic failover.

Priority order (configurable):
  1. Groq           — fastest, generous free tier
  2. OpenRouter     — broadest model selection
  3. Nvidia NIM     — enterprise-grade open models
  4. OpenAI         — high quality fallback
  5. Deterministic  — always works, no key needed

Failover triggers:
  - RateLimitError (429) → immediate skip to next
  - AuthError (401/403)  → skip (bad key)
  - TimeoutError          → skip (provider too slow)
  - ParseError            → skip (bad LLM response)
  - Any other exception   → skip with warning

Every diagnosis logs which provider was actually used.
This is visible in the compliance audit trail.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from .llm_provider import (
    BaseLLMProvider,
    DiagnosisResult,
    DeterministicFallbackProvider,
    GroqProvider,
    NvidiaNIMProvider,
    OpenAIProvider,
    OpenRouterProvider,
    ProviderError,
    RateLimitError,
    AuthError,
    TimeoutError,
    ParseError,
)

logger = logging.getLogger(__name__)


class LLMProviderChain:
    """
    Ordered chain of LLM providers with automatic failover.

    Usage:
        chain = LLMProviderChain()
        result = chain.diagnose(payment)
        print(result.provider_used)  # "groq" | "openrouter" | ... | "deterministic_fallback"
    """

    def __init__(self, providers: Optional[List[BaseLLMProvider]] = None):
        if providers is None:
            # Default priority chain
            providers = [
                GroqProvider(),
                OpenRouterProvider(),
                NvidiaNIMProvider(),
                OpenAIProvider(),
                DeterministicFallbackProvider(),  # Always last, always works
            ]
        self._providers = providers

    def get_active_providers(self) -> List[str]:
        """Return names of providers that have API keys configured."""
        return [p.name for p in self._providers if p.is_available()]

    def get_provider_status(self) -> List[dict]:
        """Return status info for all providers (for /health endpoint)."""
        return [
            {
                "name": p.name,
                "available": p.is_available(),
                "type": "llm" if p.name != "deterministic_fallback" else "deterministic",
            }
            for p in self._providers
        ]

    def diagnose(
        self,
        transaction_id: str,
        failure_code: str,
        amount: float,
        customer_name: str,
        customer_email: str,
        retry_count: int = 0,
        payment_status: str = "failed",
    ) -> DiagnosisResult:
        """
        Run diagnosis through the provider chain.

        Tries each available provider in order. On any provider error,
        logs the failure and immediately moves to the next provider.
        The deterministic fallback at the end always succeeds.

        Args:
            transaction_id:  Payment transaction ID
            failure_code:    Gateway failure code (e.g. "insufficient_funds")
            amount:          Payment amount in INR
            customer_name:   Customer display name
            customer_email:  Customer email
            retry_count:     Number of previous recovery attempts
            payment_status:  Payment status ("failed" | "abandoned")

        Returns:
            DiagnosisResult with provider_used field indicating which ran.

        Raises:
            Never — the deterministic fallback ensures this always returns.
        """
        last_error: Optional[Exception] = None

        for provider in self._providers:
            if not provider.is_available():
                logger.debug("Skipping %s — not configured", provider.name)
                continue

            try:
                logger.info("Attempting diagnosis via %s", provider.name)
                result = provider.diagnose(
                    transaction_id=transaction_id,
                    failure_code=failure_code,
                    amount=amount,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    retry_count=retry_count,
                    payment_status=payment_status,
                )
                logger.info(
                    "Diagnosis successful via %s (latency=%dms, confidence=%.2f)",
                    provider.name,
                    result.latency_ms,
                    result.confidence,
                )
                return result

            except RateLimitError as exc:
                logger.warning("Rate limit on %s — failing over: %s", provider.name, exc)
                last_error = exc

            except AuthError as exc:
                logger.warning("Auth error on %s — skipping: %s", provider.name, exc)
                last_error = exc

            except TimeoutError as exc:
                logger.warning("Timeout on %s — failing over: %s", provider.name, exc)
                last_error = exc

            except ParseError as exc:
                logger.warning("Parse error on %s — failing over: %s", provider.name, exc)
                last_error = exc

            except ProviderError as exc:
                logger.warning("Provider error on %s — failing over: %s", provider.name, exc)
                last_error = exc

            except Exception as exc:
                logger.error(
                    "Unexpected error on %s — failing over: %s",
                    provider.name,
                    exc,
                    exc_info=True,
                )
                last_error = exc

        # This should never be reached because DeterministicFallbackProvider.is_available()
        # always returns True, but guard just in case.
        logger.error(
            "All providers exhausted (last error: %s). "
            "Running emergency deterministic fallback.",
            last_error,
        )
        return DeterministicFallbackProvider().diagnose(
            transaction_id=transaction_id,
            failure_code=failure_code,
            amount=amount,
            customer_name=customer_name,
            customer_email=customer_email,
            retry_count=retry_count,
            payment_status=payment_status,
        )


# ---------------------------------------------------------------------------
# Singleton instance (module-level, shared across requests)
# ---------------------------------------------------------------------------

_chain_instance: Optional[LLMProviderChain] = None


def get_provider_chain() -> LLMProviderChain:
    """Return the shared provider chain singleton."""
    global _chain_instance
    if _chain_instance is None:
        _chain_instance = LLMProviderChain()
    return _chain_instance
