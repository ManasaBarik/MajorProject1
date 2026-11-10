"""Strict validation of AI output.

Nothing the model returns is trusted: every field is coerced, checked against
the allowed vocabulary, and missing/unsafe values are replaced with safe
defaults.  A failed validation never raises into the request cycle - it simply
flags the analysis for mandatory human review.
"""
from django.conf import settings

from .constants import CANONICAL_CATEGORIES, CATEGORY_ALIASES, PRIORITIES


class AIValidationError(Exception):
    """Raised only for programming errors, not for soft validation failures."""


def normalize_category(value):
    """Fold a raw category string onto the canonical vocabulary.

    Returns ``None`` when the value cannot be mapped, so the caller can decide
    whether to fall back to ``OTHER``.
    """
    if not isinstance(value, str):
        return None
    candidate = value.strip().upper().replace(" ", "_")
    if candidate in CANONICAL_CATEGORIES:
        return candidate
    if candidate in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[candidate]
    # Try a secondary match against the alias keys (e.g. "ROADS " handled above).
    for alias, canonical in CATEGORY_ALIASES.items():
        if alias in candidate:
            return canonical
    return None


def normalize_priority(value):
    if not isinstance(value, str):
        return None
    candidate = value.strip().upper()
    return candidate if candidate in PRIORITIES else None


def _coerce_confidence(value):
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0:
        return 0.0
    if score > 1:
        # The model sometimes returns a 0-100 scale; normalise it.
        score = score / 100.0 if score <= 100 else 1.0
    return round(score, 4)


def _clean_text(value, max_length):
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def validate_analysis(payload):
    """Return a normalised, safe analysis dict derived from ``payload``.

    Output keys:
        category, priority, summary, reasoning, confidence, requires_manual_review
    """
    if not isinstance(payload, dict):
        payload = {}

    requires_review = False

    category = normalize_category(payload.get("category"))
    if category is None:
        category = "OTHER"
        requires_review = True

    priority = normalize_priority(payload.get("priority"))
    if priority is None:
        priority = "MEDIUM"
        requires_review = True

    summary = _clean_text(payload.get("summary"), 800)
    if not summary:
        requires_review = True

    reasoning = _clean_text(
        payload.get("reasoning") or payload.get("reason"), 800
    )

    confidence = _coerce_confidence(payload.get("confidence"))
    low_confidence = settings.AI_LOW_CONFIDENCE_THRESHOLD
    if confidence is None or confidence < low_confidence:
        requires_review = True

    # Honour an explicit model/human flag as well.
    if payload.get("requires_manual_review") is True:
        requires_review = True

    return {
        "category": category,
        "priority": priority,
        "summary": summary,
        "reasoning": reasoning,
        "confidence": confidence,
        "requires_manual_review": requires_review,
    }
