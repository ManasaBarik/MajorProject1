"""Offline heuristic provider.

Used for local development, tests, and as an automatic fallback when the
Gemini API key is not configured.  It performs deterministic keyword scoring so
the whole complaint workflow remains demonstrable with no network access.
"""
from .base import AIProvider
from ..constants import (
    CATEGORY_KEYWORDS,
    HIGH_KEYWORDS,
    URGENT_KEYWORDS,
)

MODEL_NAME = "heuristic-v1"


class MockAIProvider(AIProvider):
    provider_name = "mock"

    def __init__(self, fallback_reason=""):
        self.fallback_reason = fallback_reason

    def _score_categories(self, text):
        scores = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    # Longer phrases are stronger signals than single words.
                    score += 2 if " " in keyword else 1
            if score:
                scores[category] = score
        return scores

    def _estimate_priority(self, text):
        if any(word in text for word in URGENT_KEYWORDS):
            return "CRITICAL"
        if any(word in text for word in HIGH_KEYWORDS):
            return "HIGH"
        return "MEDIUM"

    def analyze_complaint(self, complaint):
        title = (getattr(complaint, "title", "") or "").lower()
        description = (getattr(complaint, "description", "") or "").lower()
        text = f"{title} {description}"

        scores = self._score_categories(text)
        if scores:
            category, top_score = max(scores.items(), key=lambda item: item[1])
            total = sum(scores.values())
            confidence = min(0.92, 0.45 + 0.12 * top_score)
            if total > top_score:
                # Competing signals lower our certainty.
                confidence = max(0.2, confidence - 0.15)
        else:
            category = "OTHER"
            confidence = 0.3

        priority = self._estimate_priority(text)

        summary_source = (getattr(complaint, "description", "") or "").strip()
        summary = (summary_source or getattr(complaint, "title", "") or "").strip()[:240]

        message = "Offline heuristic analysis (no external AI provider used)."
        if self.fallback_reason:
            message = f"{message} {self.fallback_reason}"

        return {
            "configured": True,
            "degraded": True,
            "message": message,
            "provider": "mock",
            "model_name": MODEL_NAME,
            "category": category,
            "priority": priority,
            "summary": summary,
            "reasoning": (
                "Keyword-based heuristic classification. Configure GEMINI_API_KEY "
                "to enable large-language-model analysis."
            ),
            "confidence": round(confidence, 4),
            "requires_manual_review": confidence < 0.5,
        }
