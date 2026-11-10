"""Orchestrates complaint analysis: provider -> validation -> persistence.

The AI is advisory only.  Every result is stored on ``AIAnalysis`` for human
review; the complaint itself is never mutated here.
"""
import logging

from django.conf import settings

from apps.departments.models import CategoryDepartmentMapping

from .duplicates import find_similar_complaints
from .providers.gemini import AIProviderError, GeminiProvider
from .providers.mock import MockAIProvider
from .providers.placeholder import PlaceholderAIProvider
from .schemas import validate_analysis

logger = logging.getLogger(__name__)


def get_provider():
    """Resolve the configured provider, degrading gracefully to offline mode."""
    name = (settings.AI_PROVIDER or "none").strip().lower()
    if name == "gemini":
        if settings.GEMINI_API_KEY:
            return GeminiProvider()
        logger.info("AI_PROVIDER=gemini but GEMINI_API_KEY is unset; falling back to offline analysis.")
        return MockAIProvider(
            fallback_reason="GEMINI_API_KEY is not configured, so offline analysis was used."
        )
    if name == "mock":
        return MockAIProvider()
    return PlaceholderAIProvider()


def resolve_department(category):
    """Resolve the department for a category via the administrator mapping."""
    if not category:
        return None
    mapping = (
        CategoryDepartmentMapping.objects.filter(category=category, active=True)
        .select_related("department")
        .first()
    )
    if mapping and mapping.department and mapping.department.active:
        return mapping.department
    return None


def _provider_name(provider):
    return getattr(provider, "provider_name", provider.__class__.__name__)


def analyze_complaint(complaint, actor=None, ip_address=None, persist=True):
    """Run analysis for ``complaint`` and return a serialisable result dict."""
    provider = get_provider()
    try:
        raw = provider.analyze_complaint(complaint)
    except Exception as exc:  # noqa: BLE001 - never let AI break the request
        logger.warning("AI analysis failed for complaint %s: %s", complaint.pk, exc)
        return _persist_failure(complaint, provider, exc, actor, ip_address, persist)

    if not raw.get("configured"):
        # AI is explicitly disabled (provider "none"): preserve prior behaviour.
        return raw

    return _persist_success(complaint, provider, raw, actor, ip_address, persist)


def _similar(complaint):
    try:
        return find_similar_complaints(complaint)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Duplicate detection failed for complaint %s: %s", complaint.pk, exc)
        return []


def _persist_success(complaint, provider, raw, actor, ip_address, persist):
    from apps.complaints.models import AIAnalysis

    validated = validate_analysis(raw)
    department = resolve_department(validated["category"])
    similar = _similar(complaint)

    # A missing department mapping always needs a human to route it.
    requires_review = bool(validated["requires_manual_review"] or department is None)

    analysis = None
    if persist:
        from apps.audit.services import record_audit

        analysis = AIAnalysis.objects.create(
            complaint=complaint,
            category_prediction=validated["category"],
            priority_prediction=validated["priority"],
            department_recommendation=department,
            confidence=validated["confidence"],
            summary=validated["summary"],
            reason=validated["reasoning"],
            provider=raw.get("provider", _provider_name(provider)),
            model_name=raw.get("model_name", ""),
            raw_response=raw.get("raw_response"),
            requires_manual_review=requires_review,
            similar_complaints=similar,
        )
        record_audit(
            actor=actor,
            action="AI_ANALYSIS_COMPLETED",
            entity_type="complaint",
            entity_id=complaint.pk,
            new_value={
                "category": validated["category"],
                "priority": validated["priority"],
                "department_id": department.id if department else None,
                "confidence": validated["confidence"],
                "provider": raw.get("provider", _provider_name(provider)),
            },
            ip_address=ip_address,
        )

    return {
        "configured": True,
        "degraded": bool(raw.get("degraded", False)),
        "message": raw.get("message") or "AI analysis completed.",
        "provider": raw.get("provider", _provider_name(provider)),
        "model_name": raw.get("model_name", ""),
        "category": validated["category"],
        "priority": validated["priority"],
        "department": department.name if department else None,
        "department_id": department.id if department else None,
        "confidence": validated["confidence"],
        "summary": validated["summary"],
        "reasoning": validated["reasoning"],
        "requires_manual_review": requires_review,
        "similar_complaints": similar,
        "analysis_id": analysis.id if analysis else None,
    }


def _persist_failure(complaint, provider, exc, actor, ip_address, persist):
    from apps.complaints.models import AIAnalysis

    similar = _similar(complaint)
    analysis = None
    if persist:
        from apps.audit.services import record_audit

        analysis = AIAnalysis.objects.create(
            complaint=complaint,
            provider=_provider_name(provider),
            model_name=getattr(provider, "model", "") or "",
            requires_manual_review=True,
            similar_complaints=similar,
            reason=f"AI analysis unavailable: {exc}",
        )
        record_audit(
            actor=actor,
            action="AI_ANALYSIS_FAILED",
            entity_type="complaint",
            entity_id=complaint.pk,
            new_value={"error": str(exc)[:300]},
            ip_address=ip_address,
        )

    return {
        "configured": True,
        "degraded": True,
        "message": "AI analysis is temporarily unavailable; manual review required.",
        "provider": _provider_name(provider),
        "model_name": getattr(provider, "model", "") or "",
        "category": None,
        "priority": None,
        "department": None,
        "department_id": None,
        "confidence": None,
        "summary": "",
        "reasoning": "",
        "requires_manual_review": True,
        "similar_complaints": similar,
        "analysis_id": analysis.id if analysis else None,
    }
