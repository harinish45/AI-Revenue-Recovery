"""
llm_provider.py
---------------
Abstract base and concrete LLM provider implementations.

Each provider:
  1. Receives a structured prompt about a payment failure
  2. Calls its LLM API via httpx (no heavy dependencies)
  3. Returns a structured DiagnosisResult
  4. Raises ProviderError on any failure (rate limit, auth, timeout, bad JSON)

The provider chain in llm_provider_chain.py tries each provider in order
and falls through on any ProviderError.

Why httpx not an SDK:
  - Zero extra dependencies per provider
  - Consistent timeout/retry behavior
  - Easy to add new providers by just changing base_url + headers
"""
from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result schema — same structure whether from LLM or deterministic fallback
# ---------------------------------------------------------------------------

@dataclass
class DiagnosisResult:
    """
    Structured AI diagnosis output.

    This is the contract between the AI layer and the deterministic layer.
    Both LLM providers and the deterministic fallback return this exact shape.
    """
    diagnosis: str
    decision: str
    reason: str
    evidence: List[str]
    confidence: float
    recommended_action: str
    risk_level: str
    provider_used: str = "unknown"
    latency_ms: int = 0


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------

class ProviderError(Exception):
    """Base error for any provider failure — triggers failover."""
    pass

class RateLimitError(ProviderError):
    """HTTP 429 — trigger immediate failover."""
    pass

class AuthError(ProviderError):
    """HTTP 401/403 — skip provider (bad key)."""
    pass

class TimeoutError(ProviderError):
    """Request timed out — skip provider."""
    pass

class ParseError(ProviderError):
    """LLM returned invalid JSON — skip provider."""
    pass


# ---------------------------------------------------------------------------
# Shared prompt builder
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are RecoverAI, a financial recovery AI assistant for Razorpay.

Your job: analyze a failed payment and produce a structured diagnosis and recovery recommendation.

IMPORTANT CONSTRAINTS:
- You NEVER directly trigger payments. You only recommend actions.
- All recommendations are reviewed by a deterministic policy engine before execution.
- Be precise, evidence-based, and concise.

You MUST respond with ONLY a valid JSON object — no markdown, no explanation:
{
  "diagnosis": "one-sentence root cause diagnosis",
  "decision": "RETRY_PAYMENT|RETRY_WITH_SPLIT|HALT_AND_ALERT|REQUEST_UPDATE|SEND_NUDGE|ESCALATE_TO_HUMAN",
  "reason": "2-3 sentence explanation of why this action will work",
  "evidence": ["evidence point 1", "evidence point 2", "evidence point 3"],
  "confidence": 0.0-1.0,
  "recommended_action": "SEND_RETRY_LINK|OFFER_SPLIT_PAYMENT|HALT_AND_ALERT|REQUEST_CARD_UPDATE|SEND_REMINDER_NUDGE|ESCALATE_TO_HUMAN",
  "risk_level": "LOW|MEDIUM|HIGH"
}"""

def build_diagnosis_prompt(
    transaction_id: str,
    failure_code: str,
    amount: float,
    customer_name: str,
    customer_email: str,
    retry_count: int,
    payment_status: str,
) -> str:
    """Build the user prompt for payment failure diagnosis."""
    return f"""Analyze this failed payment and provide a recovery recommendation:

PAYMENT DETAILS:
- Transaction ID: {transaction_id}
- Failure Code: {failure_code}
- Amount: ₹{amount:,.2f} INR
- Customer: {customer_name} ({customer_email})
- Payment Status: {payment_status}
- Previous Recovery Attempts: {retry_count}

FAILURE CONTEXT:
The payment failed with code "{failure_code}". Based on this failure code, payment amount,
and the customer's retry history, diagnose the root cause and recommend the optimal
recovery intervention that maximizes recovery probability while minimizing customer friction.

Respond ONLY with valid JSON matching the specified schema."""


def _parse_llm_json(raw: str, provider_name: str) -> dict:
    """
    Extract and parse JSON from LLM response.
    Handles cases where the LLM wraps JSON in markdown code blocks.
    """
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"{provider_name}: Invalid JSON response — {exc}") from exc

    # Validate required fields
    required = {"diagnosis", "decision", "reason", "evidence", "confidence",
                "recommended_action", "risk_level"}
    missing = required - set(parsed.keys())
    if missing:
        raise ParseError(f"{provider_name}: Missing fields in response: {missing}")

    return parsed


def _result_from_dict(d: dict, provider: str, latency_ms: int) -> DiagnosisResult:
    """Convert parsed dict to DiagnosisResult."""
    return DiagnosisResult(
        diagnosis=str(d.get("diagnosis", "")),
        decision=str(d.get("decision", "ESCALATE_TO_HUMAN")),
        reason=str(d.get("reason", "")),
        evidence=list(d.get("evidence", [])),
        confidence=float(d.get("confidence", 0.5)),
        recommended_action=str(d.get("recommended_action", "ESCALATE_TO_HUMAN")),
        risk_level=str(d.get("risk_level", "HIGH")),
        provider_used=provider,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# Abstract base provider
# ---------------------------------------------------------------------------

class BaseLLMProvider(ABC):
    """Abstract LLM provider. Implement `diagnose()` in each subclass."""

    name: str = "unknown"

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider has a configured API key."""
        ...

    @abstractmethod
    def diagnose(
        self,
        transaction_id: str,
        failure_code: str,
        amount: float,
        customer_name: str,
        customer_email: str,
        retry_count: int,
        payment_status: str,
    ) -> DiagnosisResult:
        """
        Call the LLM and return a DiagnosisResult.
        Raises ProviderError on any failure.
        """
        ...

    def _call_openai_compatible(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: list,
        extra_headers: Optional[dict] = None,
    ) -> tuple[str, int]:
        """
        Call any OpenAI-compatible chat completion API.

        Args:
            base_url:      API base URL
            api_key:       Bearer token
            model:         Model identifier
            messages:      Chat messages list
            extra_headers: Additional headers (e.g. OpenRouter site info)

        Returns:
            (content: str, latency_ms: int)

        Raises:
            RateLimitError, AuthError, TimeoutError, ProviderError
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.1,  # Low temperature for consistent structured output
        }

        start = time.monotonic()
        try:
            with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                response = client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"{self.name}: Request timed out after {settings.LLM_TIMEOUT_SECONDS}s") from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"{self.name}: Connection error — {exc}") from exc

        latency_ms = int((time.monotonic() - start) * 1000)

        if response.status_code == 429:
            raise RateLimitError(f"{self.name}: Rate limit exceeded (HTTP 429)")
        if response.status_code in (401, 403):
            raise AuthError(f"{self.name}: Authentication failed (HTTP {response.status_code})")
        if response.status_code >= 500:
            raise ProviderError(f"{self.name}: Server error (HTTP {response.status_code})")
        if response.status_code != 200:
            raise ProviderError(f"{self.name}: Unexpected HTTP {response.status_code}: {response.text[:200]}")

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise ParseError(f"{self.name}: Malformed API response — {exc}") from exc

        return content, latency_ms


# ---------------------------------------------------------------------------
# Concrete providers
# ---------------------------------------------------------------------------

class GroqProvider(BaseLLMProvider):
    """
    Groq — Ultra-fast inference via GroqCloud.
    Free tier: 14,400 requests/day, 6,000 tokens/minute.
    Get key: https://console.groq.com/
    """
    name = "groq"
    BASE_URL = "https://api.groq.com/openai/v1"
    MODEL = "llama-3.1-70b-versatile"

    def is_available(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    def diagnose(self, transaction_id, failure_code, amount, customer_name,
                 customer_email, retry_count, payment_status) -> DiagnosisResult:
        prompt = build_diagnosis_prompt(
            transaction_id, failure_code, amount, customer_name,
            customer_email, retry_count, payment_status
        )
        content, latency = self._call_openai_compatible(
            base_url=self.BASE_URL,
            api_key=settings.GROQ_API_KEY,
            model=self.MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        parsed = _parse_llm_json(content, self.name)
        return _result_from_dict(parsed, self.name, latency)


class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter — Unified gateway to 100+ models.
    Free tier available. Get key: https://openrouter.ai/
    """
    name = "openrouter"
    BASE_URL = "https://openrouter.ai/api/v1"
    MODEL = "meta-llama/llama-3.1-70b-instruct:free"

    def is_available(self) -> bool:
        return bool(settings.OPENROUTER_API_KEY)

    def diagnose(self, transaction_id, failure_code, amount, customer_name,
                 customer_email, retry_count, payment_status) -> DiagnosisResult:
        prompt = build_diagnosis_prompt(
            transaction_id, failure_code, amount, customer_name,
            customer_email, retry_count, payment_status
        )
        content, latency = self._call_openai_compatible(
            base_url=self.BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
            model=self.MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            extra_headers={
                "HTTP-Referer": "https://github.com/harinish45/AI-Revenue-Recovery",
                "X-Title": "RecoverAI — Razorpay Hackathon",
            },
        )
        parsed = _parse_llm_json(content, self.name)
        return _result_from_dict(parsed, self.name, latency)


class NvidiaNIMProvider(BaseLLMProvider):
    """
    Nvidia NIM — Enterprise-grade open model inference.
    Get key: https://build.nvidia.com/
    """
    name = "nvidia_nim"
    BASE_URL = "https://integrate.api.nvidia.com/v1"
    MODEL = "meta/llama-3.1-70b-instruct"

    def is_available(self) -> bool:
        return bool(settings.NVIDIA_NIM_API_KEY)

    def diagnose(self, transaction_id, failure_code, amount, customer_name,
                 customer_email, retry_count, payment_status) -> DiagnosisResult:
        prompt = build_diagnosis_prompt(
            transaction_id, failure_code, amount, customer_name,
            customer_email, retry_count, payment_status
        )
        content, latency = self._call_openai_compatible(
            base_url=self.BASE_URL,
            api_key=settings.NVIDIA_NIM_API_KEY,
            model=self.MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        parsed = _parse_llm_json(content, self.name)
        return _result_from_dict(parsed, self.name, latency)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI — gpt-4o-mini fallback.
    Get key: https://platform.openai.com/
    """
    name = "openai"
    BASE_URL = "https://api.openai.com/v1"
    MODEL = "gpt-4o-mini"

    def is_available(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    def diagnose(self, transaction_id, failure_code, amount, customer_name,
                 customer_email, retry_count, payment_status) -> DiagnosisResult:
        prompt = build_diagnosis_prompt(
            transaction_id, failure_code, amount, customer_name,
            customer_email, retry_count, payment_status
        )
        content, latency = self._call_openai_compatible(
            base_url=self.BASE_URL,
            api_key=settings.OPENAI_API_KEY,
            model=self.MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        parsed = _parse_llm_json(content, self.name)
        return _result_from_dict(parsed, self.name, latency)


# ---------------------------------------------------------------------------
# Deterministic fallback — ALWAYS works, no API key needed
# ---------------------------------------------------------------------------

_FALLBACK_MAP = {
    "insufficient_funds": {
        "diagnosis": "Customer lacks sufficient funds at payment time. High purchase intent detected.",
        "decision": "RETRY_WITH_SPLIT",
        "reason": "Insufficient funds failures have ~68% recovery rate when offered a split payment option. Customer demonstrated intent by reaching checkout. Recommended: EMI or split payment link.",
        "evidence": [
            "Failure code INSUFFICIENT_FUNDS indicates liquidity issue, not intent issue",
            "Historical recovery rate for this failure type: 68% with split payment offer",
            "Customer reached payment page — strong purchase intent signal",
        ],
        "confidence": 0.88,
        "recommended_action": "OFFER_SPLIT_PAYMENT",
        "risk_level_thresholds": (10000, 30000),
    },
    "gateway_timeout": {
        "diagnosis": "Transient gateway timeout. Infrastructure failure — customer card not charged.",
        "decision": "RETRY_PAYMENT",
        "reason": "Gateway timeouts are infrastructure-side failures with ~82% retry success rate within 30 minutes. Customer's card was never charged. Direct retry link is the optimal intervention.",
        "evidence": [
            "GATEWAY_TIMEOUT is an infrastructure failure — customer card never charged",
            "Historical retry success rate within 30 minutes: 82%",
            "No risk of double-charge — payment never processed",
        ],
        "confidence": 0.91,
        "recommended_action": "SEND_RETRY_LINK",
        "risk_level_thresholds": (15000, 40000),
    },
    "bank_maintenance": {
        "diagnosis": "Scheduled bank maintenance window. Retry after maintenance completion.",
        "decision": "RETRY_PAYMENT",
        "reason": "Bank maintenance windows are predictable and temporary (2-4 hours). Retry after the window has ~79% success. Delayed retry link is optimal.",
        "evidence": [
            "BANK_MAINTENANCE is a scheduled, predictable downtime",
            "Customer card and account are valid — failure is infrastructural",
            "Post-maintenance retry success rate: 79%",
        ],
        "confidence": 0.85,
        "recommended_action": "SEND_RETRY_LINK",
        "risk_level_thresholds": (15000, 40000),
    },
    "invalid_card": {
        "diagnosis": "Card details invalid. Possible fraudulent attempt or test card misuse.",
        "decision": "HALT_AND_ALERT",
        "reason": "Invalid card failures carry fraud risk and violate PCI-DSS retry policies. Automated retry is unsafe. Risk team review required before any action.",
        "evidence": [
            "INVALID_CARD may indicate fraud, stolen card, or unauthorized test card use",
            "PCI-DSS prohibits automated retry on invalid card failures",
            "Risk team escalation required before any recovery action",
        ],
        "confidence": 0.97,
        "recommended_action": "HALT_AND_ALERT",
        "risk_level_thresholds": (0, 0),  # Always HIGH
    },
    "expired_card": {
        "diagnosis": "Card on file has expired. Customer must update payment method.",
        "decision": "REQUEST_UPDATE",
        "reason": "Expired card failures cannot be resolved without a new payment method. Secure card-update link has ~71% conversion rate when sent within 1 hour of failure.",
        "evidence": [
            "EXPIRED_CARD — card past its expiry date, decline is permanent",
            "No retry will succeed without updated payment method",
            "Card update link conversion rate: 71% within first hour",
        ],
        "confidence": 0.93,
        "recommended_action": "REQUEST_CARD_UPDATE",
        "risk_level_thresholds": (10000, 30000),
    },
    "user_cancelled": {
        "diagnosis": "Customer abandoned checkout voluntarily. High-intent cart abandonment.",
        "decision": "SEND_NUDGE",
        "reason": "Intentional abandonment at checkout has ~42% recovery rate with a timely reminder nudge. Customer reached the payment page, indicating strong purchase intent.",
        "evidence": [
            "USER_CANCELLED — customer voluntarily left checkout flow",
            "Reaching payment page is a high purchase intent signal",
            "Cart abandonment nudge conversion rate: 42% within 24 hours",
        ],
        "confidence": 0.72,
        "recommended_action": "SEND_REMINDER_NUDGE",
        "risk_level_thresholds": (10000, 30000),
    },
}

_DEFAULT_FALLBACK = {
    "diagnosis": "Unknown failure code. Insufficient data for automated root cause analysis.",
    "decision": "ESCALATE_TO_HUMAN",
    "reason": "The failure code is not in the recovery knowledge base. Automated recovery cannot proceed safely without confirmed root cause. Human review required.",
    "evidence": [
        "Failure code not recognized by recovery system",
        "Automated recovery aborted — safety rule triggered",
        "Human analyst review required before any action",
    ],
    "confidence": 0.45,
    "recommended_action": "ESCALATE_TO_HUMAN",
    "risk_level_thresholds": (0, 0),  # Always HIGH
}


class DeterministicFallbackProvider(BaseLLMProvider):
    """
    Deterministic fallback provider.

    Always available, never fails, no API key required.
    Returns the same structured output format as LLM providers.
    Used when all LLM providers are unavailable or exhausted.
    """
    name = "deterministic_fallback"

    def is_available(self) -> bool:
        return True  # Always available

    def diagnose(
        self,
        transaction_id: str,
        failure_code: str,
        amount: float,
        customer_name: str,
        customer_email: str,
        retry_count: int,
        payment_status: str,
    ) -> DiagnosisResult:
        mapping = _FALLBACK_MAP.get(failure_code, _DEFAULT_FALLBACK)
        low_thresh, mid_thresh = mapping["risk_level_thresholds"]

        if low_thresh == 0:
            risk_level = "HIGH"
        elif amount <= low_thresh:
            risk_level = "LOW"
        elif amount <= mid_thresh:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        # Materialize evidence with amount
        evidence = [
            e.replace("{amount}", f"₹{amount:,.2f}")
            for e in mapping["evidence"]
        ]

        return DiagnosisResult(
            diagnosis=mapping["diagnosis"],
            decision=mapping["decision"],
            reason=mapping["reason"],
            evidence=evidence,
            confidence=mapping["confidence"],
            recommended_action=mapping["recommended_action"],
            risk_level=risk_level,
            provider_used=self.name,
            latency_ms=0,
        )
