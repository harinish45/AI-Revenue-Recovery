import httpx
import json
import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, ConfigDict

class LLMDecision(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    decision: str
    reason: str
    evidence: List[str]
    confidence: float

class BaseLLMProvider:
    def get_decision(self, payment_data: Dict[str, Any], history: Dict[str, Any]) -> Optional[LLMDecision]:
        raise NotImplementedError

class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o-mini"
        self.system_prompt = """You are an expert AI Revenue Recovery Agent for Razorpay merchants.
Your task is to analyze a failed payment and customer history, then recommend a bounded recovery action.

STRICT JSON SCHEMA REQUIREMENT:
You MUST output ONLY valid JSON matching this exact schema. No markdown, no explanations, no extra text.
{
  "decision": "RETRY_PAYMENT" | "PAYMENT_LINK" | "CUSTOMER_REMINDER" | "HUMAN_REVIEW",
  "reason": "string explaining why",
  "evidence": ["string fact 1", "string fact 2"],
  "confidence": 0.0 to 1.0
}

RULES:
- decision MUST be exactly one of the 4 allowed strings.
- evidence MUST be derived ONLY from the provided data.
- If data is insufficient or failure is unknown, use HUMAN_REVIEW with low confidence.
"""

    def get_decision(self, payment_data: Dict[str, Any], history: Dict[str, Any]) -> Optional[LLMDecision]:
        if not self.api_key:
            return None
        
        prompt = f"Payment Data: {json.dumps(payment_data)}\nCustomer History: {json.dumps(history)}"
        
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    }
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return LLMDecision(**parsed)
        except Exception:
            return None
