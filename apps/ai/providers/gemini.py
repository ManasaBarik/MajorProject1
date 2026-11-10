"""Google Gemini provider.

Talks to the Gemini ``generateContent`` REST endpoint using only the Python
standard library (no third-party HTTP dependency).  The API key is read from
Django settings (sourced from the server-side ``.env``) and is never exposed to
the browser.
"""
import json
import time
import urllib.error
import urllib.request

from django.conf import settings

from .base import AIProvider
from ..constants import CANONICAL_CATEGORIES, PRIORITIES
from ..prompts import SYSTEM_INSTRUCTION, build_user_prompt

PROVIDER_NAME = "gemini"

# Structured-output schema so the model must return schema-conforming JSON.
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "category": {"type": "STRING", "enum": list(CANONICAL_CATEGORIES)},
        "priority": {"type": "STRING", "enum": list(PRIORITIES)},
        "summary": {"type": "STRING"},
        "confidence": {"type": "NUMBER"},
        "reasoning": {"type": "STRING"},
        "requires_manual_review": {"type": "BOOLEAN"},
    },
    "required": ["category", "priority", "summary", "confidence"],
}


class AIProviderError(Exception):
    """Raised when the upstream provider cannot produce a result."""


class GeminiProvider(AIProvider):
    provider_name = "gemini"

    def __init__(self, api_key=None, model=None, api_base=None, timeout=None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.api_base = (api_base or settings.GEMINI_API_BASE).rstrip("/")
        self.timeout = timeout or settings.AI_REQUEST_TIMEOUT
        self.max_retries = settings.AI_MAX_RETRIES

    def _endpoint(self):
        return f"{self.api_base}/models/{self.model}:generateContent"

    def _build_body(self, complaint):
        return {
            "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
            "contents": [
                {"role": "user", "parts": [{"text": build_user_prompt(complaint)}]}
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
            },
        }

    def _post(self, body):
        request = urllib.request.Request(
            self._endpoint(),
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                last_error = exc
                # Retry only on rate limiting / transient server errors.
                if exc.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                detail = exc.read().decode("utf-8", "replace")[:500]
                raise AIProviderError(f"Gemini HTTP {exc.code}: {detail}") from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise AIProviderError(f"Gemini request failed: {exc}") from exc
        raise AIProviderError(f"Gemini request failed: {last_error}")

    @staticmethod
    def _parse_candidate(payload):
        candidates = payload.get("candidates") or []
        if not candidates:
            feedback = payload.get("promptFeedback") or {}
            raise AIProviderError(f"Gemini returned no candidates: {feedback}")
        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise AIProviderError("Gemini returned an empty response.")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIProviderError(f"Gemini returned malformed JSON: {text[:200]}") from exc

    def analyze_complaint(self, complaint):
        parsed = self._parse_candidate(self._post(self._build_body(complaint)))
        return {
            "configured": True,
            "message": "AI analysis completed.",
            "provider": PROVIDER_NAME,
            "model_name": self.model,
            "category": parsed.get("category"),
            "priority": parsed.get("priority"),
            "summary": parsed.get("summary", ""),
            "reasoning": parsed.get("reasoning", ""),
            "confidence": parsed.get("confidence"),
            "requires_manual_review": parsed.get("requires_manual_review", False),
            "raw_response": parsed,
        }
