import calendar as _cal
from statistics import fmean
from datetime import timedelta
from django.db.models import Count, Prefetch
from django.db.models.functions import ExtractMonth, ExtractYear
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from common.permissions import IsOfficerOrAdmin, IsAdministrator, IsEngineerOfficerOrAdmin
from common.responses import success
from common.schemas import APIEnvelopeSerializer
from apps.complaints.models import Complaint, ComplaintStatusHistory
from apps.applications.models import BusinessApplication


_OPEN_COMPLAINT_STATUSES = {
    "SUBMITTED", "AI_PROCESSING", "CLASSIFIED", "ASSIGNED",
    "IN_PROGRESS", "ON_HOLD", "RESOLUTION_SUBMITTED",
    "VERIFICATION_PENDING", "REOPENED",
}

_CLOSED_COMPLAINT_STATUSES = {"RESOLVED", "CLOSED", "REJECTED"}


class OverviewView(APIView):
    permission_classes = [IsEngineerOfficerOrAdmin]

    @extend_schema(responses=APIEnvelopeSerializer)
    def get(self, request):
        complaints = Complaint.objects.all()
        applications = BusinessApplication.objects.all()
        total = complaints.count()
        open_qs = complaints.exclude(status__in=_CLOSED_COMPLAINT_STATUSES)
        open_count = open_qs.count()
        resolved_count = complaints.filter(status__in={"RESOLVED", "CLOSED"}).count()

        overdue_count = 0
        try:
            from django.utils import timezone
            now = timezone.now()
            cutoff = now - timedelta(days=14)
            overdue_count = (
                open_qs
                .filter(created_at__lte=cutoff)
                .count()
            )
        except Exception:
            pass

        resolution_events = ComplaintStatusHistory.objects.filter(
            new_status__in={"RESOLVED", "CLOSED"},
        ).order_by("-created_at")
        resolved = Complaint.objects.filter(
            status__in={"RESOLVED", "CLOSED"},
        ).prefetch_related(
            Prefetch("history", queryset=resolution_events, to_attr="resolution_events"),
        )
        resolution_hours = []
        for complaint in resolved:
            if complaint.resolution_events:
                duration = complaint.resolution_events[0].created_at - complaint.created_at
                resolution_hours.append(duration.total_seconds() / 3600)
        avg_resolution_hours = round(fmean(resolution_hours), 2) if resolution_hours else None

        total_applications = applications.count()
        pending_applications = applications.exclude(
            status__in={"APPROVED", "REJECTED", "COMPLETED", "CANCELLED"}
        ).count()

        return success({
            "total_complaints": total,
            "open_complaints": open_count,
            "resolved_complaints": resolved_count,
            "overdue_complaints": overdue_count,
            "average_resolution_time_hours": avg_resolution_hours,
            "total_applications": total_applications,
            "pending_applications": pending_applications,
        })


class CategoriesView(APIView):
    permission_classes = [IsEngineerOfficerOrAdmin]

    @extend_schema(responses=APIEnvelopeSerializer)
    def get(self, request):
        rows = list(
            Complaint.objects
            .exclude(category="")
            .values("category")
            .annotate(count=Count("id"))
            .order_by("-count", "category")
        )
        result = [
            {"category": r["category"], "count": r["count"]}
            for r in rows
        ]
        return success(result)


class DepartmentsView(APIView):
    permission_classes = [IsEngineerOfficerOrAdmin]

    @extend_schema(responses=APIEnvelopeSerializer)
    def get(self, request):
        rows = list(
            Complaint.objects
            .filter(department__isnull=False)
            .values("department_id", "department__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        result = [
            {"department": r["department__name"] or "Unknown", "count": r["count"]}
            for r in rows
        ]
        return success(result)


class WardsView(APIView):
    permission_classes = [IsEngineerOfficerOrAdmin]

    @extend_schema(responses=APIEnvelopeSerializer)
    def get(self, request):
        rows = list(
            Complaint.objects
            .exclude(ward="")
            .values("ward")
            .annotate(count=Count("id"))
            .order_by("-count", "ward")
        )
        result = [
            {"ward": r["ward"], "count": r["count"]}
            for r in rows
        ]
        return success(result)


class TrendsView(APIView):
    permission_classes = [IsEngineerOfficerOrAdmin]

    @extend_schema(responses=APIEnvelopeSerializer)
    def get(self, request):
        rows = list(
            Complaint.objects
            .annotate(
                year=ExtractYear("created_at"),
                month=ExtractMonth("created_at"),
            )
            .values("year", "month")
            .annotate(complaints=Count("id"))
            .order_by("year", "month")
        )
        resolved_rows = (
            ComplaintStatusHistory.objects
            .filter(new_status__in={"RESOLVED", "CLOSED"})
            .annotate(year=ExtractYear("created_at"), month=ExtractMonth("created_at"))
            .values("year", "month")
            .annotate(resolved=Count("complaint", distinct=True))
        )
        resolved_by_period = {
            (row["year"], row["month"]): row["resolved"]
            for row in resolved_rows
        }
        month_abbr = [m[:3] for m in _cal.month_name if m]
        result = []
        for r in rows:
            result.append({
                "month": month_abbr[r["month"] - 1] if 1 <= r["month"] <= 12 else str(r["month"]),
                "complaints": r["complaints"],
                "resolved": resolved_by_period.get((r["year"], r["month"]), 0),
            })
        return success(result)


class MapComplaintsView(APIView):
    permission_classes = [IsEngineerOfficerOrAdmin]

    @extend_schema(responses=APIEnvelopeSerializer)
    def get(self, request):
        data = list(
            Complaint.objects
            .values(
                "id", "latitude", "longitude",
                "priority", "status", "category", "ward",
            )
        )
        sanitized = []
        for row in data:
            sanitized.append({
                "id": row["id"],
                "latitude": float(row["latitude"]) if row["latitude"] is not None else None,
                "longitude": float(row["longitude"]) if row["longitude"] is not None else None,
                "priority": row["priority"],
                "status": row["status"],
                "category": row["category"],
                "ward": row["ward"] or "",
            })
        return success(sanitized)


class MapHeatmapView(APIView):
    permission_classes = [IsEngineerOfficerOrAdmin]

    @extend_schema(responses=APIEnvelopeSerializer)
    def get(self, request):
        priority_weight = {"LOW": 1, "MEDIUM": 2, "HIGH": 4, "CRITICAL": 8}
        buckets = {}
        for c in Complaint.objects.all().values("latitude", "longitude", "priority"):
            try:
                lat = round(float(c["latitude"]), 2)
                lng = round(float(c["longitude"]), 2)
            except (TypeError, ValueError):
                continue
            key = (lat, lng)
            w = priority_weight.get(c["priority"], 1)
            cur_count, cur_weight = buckets.get(key, (0, 0))
            buckets[key] = (cur_count + 1, cur_weight + w)
        if not buckets:
            return success([])
        max_intensity = max(v[1] for v in buckets.values()) or 1
        result = []
        for (lat, lng), (count, weight) in buckets.items():
            intensity = round(min(weight / max_intensity, 1.0), 4)
            result.append({"lat": lat, "lng": lng, "intensity": intensity})
        return success(result)
