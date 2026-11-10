"""Lightweight duplicate / near-duplicate detection.

Pure-Python TF-IDF + cosine similarity with geographic and temporal gating, so
no numpy/scikit-learn dependency is required.  Computed independently of the
LLM so it still works when AI is disabled.
"""
import math
import re
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can",
    "her", "was", "one", "our", "out", "has", "have", "been", "this", "that",
    "with", "from", "they", "there", "here", "into", "very", "near", "also",
    "its", "his", "she", "him", "who", "why", "how", "what", "when", "where",
    "will", "would", "there", "their", "about", "after", "before", "please",
    "kindly", "request", "complaint",
}

MAX_CANDIDATES = 300
DEFAULT_WINDOW_DAYS = 90
MAX_DISTANCE_KM = 3.0


def tokenize(text):
    return [
        token
        for token in TOKEN_RE.findall((text or "").lower())
        if token not in STOPWORDS and len(token) > 2
    ]


def _tfidf_vectors(documents):
    total = len(documents)
    document_frequency = {}
    for doc in documents:
        for token in set(doc):
            document_frequency[token] = document_frequency.get(token, 0) + 1
    idf = {
        token: math.log((1 + total) / (1 + freq)) + 1
        for token, freq in document_frequency.items()
    }
    vectors = []
    for doc in documents:
        if not doc:
            vectors.append({})
            continue
        term_frequency = {}
        for token in doc:
            term_frequency[token] = term_frequency.get(token, 0) + 1
        length = len(doc)
        vectors.append({
            token: (count / length) * idf.get(token, 0.0)
            for token, count in term_frequency.items()
        })
    return vectors


def cosine_similarity(a, b):
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    numerator = sum(a[token] * b[token] for token in common)
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return numerator / (norm_a * norm_b)


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def _document(complaint):
    return tokenize(f"{complaint.title or ''} {complaint.description or ''}")


def find_similar_complaints(complaint, limit=3, threshold=None):
    """Return up to ``limit`` existing complaints that look like this one."""
    from apps.complaints.models import Complaint

    threshold = settings.AI_SIMILARITY_THRESHOLD if threshold is None else threshold
    since = timezone.now() - timedelta(days=DEFAULT_WINDOW_DAYS)

    queryset = (
        Complaint.objects.filter(created_at__gte=since)
        .exclude(pk=complaint.pk)
        .exclude(status__in=["REJECTED", "CLOSED"])
    )
    if complaint.category:
        queryset = queryset.filter(category=complaint.category)
    queryset = list(
        queryset.select_related("department").order_by("-created_at")[:MAX_CANDIDATES]
    )

    if not queryset:
        return []

    target_lat = float(complaint.latitude) if complaint.latitude is not None else None
    target_lon = float(complaint.longitude) if complaint.longitude is not None else None

    documents = [_document(complaint)] + [_document(c) for c in queryset]
    vectors = _tfidf_vectors(documents)
    target_vector = vectors[0]

    matches = []
    for candidate, vector in zip(queryset, vectors[1:]):
        score = cosine_similarity(target_vector, vector)
        if score < threshold:
            continue
        distance = None
        if (
            target_lat is not None
            and target_lon is not None
            and candidate.latitude is not None
            and candidate.longitude is not None
        ):
            distance = haversine_km(
                target_lat,
                target_lon,
                float(candidate.latitude),
                float(candidate.longitude),
            )
            if distance > MAX_DISTANCE_KM:
                continue
        matches.append({
            "id": candidate.pk,
            "complaint_number": candidate.complaint_number,
            "title": candidate.title,
            "status": candidate.status,
            "category": candidate.category,
            "similarity": round(score, 3),
            "distance_km": round(distance, 2) if distance is not None else None,
        })

    matches.sort(key=lambda item: item["similarity"], reverse=True)
    return matches[:limit]
