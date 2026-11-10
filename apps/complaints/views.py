from django.shortcuts import get_object_or_404
import logging

from django.conf import settings
from rest_framework import viewsets, status as http_status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction
from common.permissions import HasRole, IsAdministrator, IsOfficerOrAdmin, IsEngineerOfficerOrAdmin
from common.responses import success
from common.pagination import paginated_success
from .models import (
    Complaint, ComplaintImage, ComplaintAssignment,
    ComplaintFeedback, AIAnalysis, ComplaintVideo, ComplaintResolution,
)
from .serializers import (
    ComplaintSerializer, ComplaintListSerializer,
    ComplaintCreateSerializer, ComplaintImageSerializer,
    ComplaintFeedbackSerializer, AIAnalysisSerializer,
)
from .services import transition, ensure_initial_history, InvalidStatusTransition
from .validators import validate_upload

logger = logging.getLogger(__name__)


class IsOfficerEngineer(HasRole):
    roles = ("OFFICER", "ENGINEER")


class IsEngineerOnly(HasRole):
    roles = ("ENGINEER",)


class IsOfficerOnly(HasRole):
    roles = ("OFFICER",)


def _can_view_complaint(user, complaint):
    if user.role == "ADMINISTRATOR":
        return True
    if complaint.citizen_id == user.id:
        return True
    if user.role == "OFFICER":
        if complaint.status in ("SUBMITTED", "AI_PROCESSING") and not complaint.department_id:
            return hasattr(user, "officer_profile")
        profile = getattr(user, "officer_profile", None)
        return bool(profile and complaint.department_id == profile.department_id)
    if user.role == "ENGINEER":
        return complaint.assigned_engineer_id == user.id
    return False


class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.none()
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return ComplaintCreateSerializer
        if self.action == "list":
            return ComplaintListSerializer
        return ComplaintSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        u = self.request.user
        q = Complaint.objects.select_related(
            "citizen", "department", "assigned_engineer",
        ).prefetch_related(
            "images", "history", "history__changed_by",
            "ai_analyses", "ai_analyses__department_recommendation",
            "ai_analyses__human_department", "feedback", "resolutions",
            "resolutions__submitted_by", "resolutions__verified_by",
        )
        if u.role == "ADMINISTRATOR":
            return q
        if u.role == "CITIZEN":
            return q.filter(citizen=u)
        if u.role == "OFFICER" and hasattr(u, "officer_profile"):
            from django.db.models import Q
            return q.filter(
                Q(department=u.officer_profile.department)
                | Q(status__in=["SUBMITTED", "AI_PROCESSING"], department__isnull=True)
            )
        if u.role == "ENGINEER":
            return q.filter(assigned_engineer_id=u.id)
        return q.none()

    @action(detail=False, methods=["get"], url_path="categories")
    def categories(self, request):
        return success([value for value, _label in Complaint.Category.choices])

    def get_object(self):
        obj = super().get_object()
        if not _can_view_complaint(self.request.user, obj):
            from rest_framework.exceptions import NotFound
            raise NotFound()
        return obj

    def list(self, request):
        return paginated_success(
            self.filter_queryset(self.get_queryset()),
            self.get_serializer_class(),
            request,
            view=self,
        )

    def filter_queryset(self, queryset):
        params = self.request.query_params
        for field in ("status", "priority", "ward"):
            value = params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        department = params.get("department", params.get("department_id"))
        if department:
            queryset = queryset.filter(department_id=department)
        search = params.get("search", "").strip()
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(category__icontains=search)
                | Q(address__icontains=search)
                | Q(ward__icontains=search)
            )
        ordering = params.get("ordering", "-created_at")
        allowed_ordering = {"created_at", "-created_at", "updated_at", "-updated_at", "status", "-status", "priority", "-priority"}
        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering, "id")
        return queryset

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        return success(self.get_serializer(obj).data)

    def create(self, request, *args, **kwargs):
        if request.user.role != "CITIZEN":
            raise PermissionDenied("Only citizens may submit complaints.")
        obj = self._create_complaint(request)
        self._run_auto_analysis(obj, request)
        obj.refresh_from_db()
        return success(ComplaintSerializer(obj).data, "Complaint submitted.", 201)

    @transaction.atomic
    def _create_complaint(self, request):
        image = request.FILES.get("image") or None
        video = request.FILES.get("video") or None
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = {k: v for k, v in s.validated_data.items() if k not in ("image", "video")}
        obj = Complaint.objects.create(citizen=request.user, **data)
        ensure_initial_history(obj)
        from apps.notifications.services import create_notification
        from apps.audit.services import record_audit

        create_notification(
            recipient=request.user,
            title="Complaint submitted",
            message=f"Your complaint '{obj.title}' was submitted successfully.",
            notification_type="complaint",
            related_object_type="complaint",
            related_object_id=obj.pk,
        )
        record_audit(
            actor=request.user,
            action="COMPLAINT_CREATED",
            entity_type="complaint",
            entity_id=obj.pk,
            new_value={"status": obj.status, "title": obj.title},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        if image:
            validate_upload(image, allowed_types={"jpg", "jpeg", "png", "webp"})
            ComplaintImage.objects.create(
                complaint=obj, file=image,
                metadata={"content_type": image.content_type},
            )
        if video:
            ComplaintVideo.objects.create(complaint=obj, file=video)
        return obj

    def _run_auto_analysis(self, complaint, request):
        """Run AI triage right after submission and move to AI_PROCESSING.

        Never raises: a failing provider must not break complaint submission.
        """
        if not settings.AI_AUTO_ANALYZE:
            return
        ip_address = request.META.get("REMOTE_ADDR")
        try:
            from apps.ai.services import analyze_complaint
            result = analyze_complaint(
                complaint, actor=request.user, ip_address=ip_address,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Auto AI analysis failed for complaint %s", complaint.pk)
            return
        if not result.get("configured"):
            return
        if complaint.status == Complaint.Status.SUBMITTED:
            try:
                transition(
                    complaint,
                    Complaint.Status.AI_PROCESSING,
                    request.user,
                    "AI analysis completed; awaiting officer review.",
                    ip_address,
                )
            except InvalidStatusTransition:
                logger.warning("Could not move complaint %s to AI_PROCESSING", complaint.pk)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.citizen_id != request.user.id or obj.status != Complaint.Status.SUBMITTED:
            raise PermissionDenied(
                "Only submitted complaints can be edited by their owner."
            )
        s = ComplaintListSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return success(ComplaintSerializer(obj).data, "Complaint updated.")

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        c = self.get_object()
        out = []
        for h in c.history.select_related("changed_by").all():
            out.append({
                "status": h.new_status,
                "timestamp": h.created_at,
                "actor": h.changed_by.name if h.changed_by else "System",
                "remarks": h.remarks or "",
            })
        return success(out)

    @action(detail=True, methods=["post"], url_path="images")
    def upload_images(self, request, pk=None):
        c = self.get_object()
        if c.citizen_id != request.user.id:
            raise PermissionDenied("Only the complaint owner may upload images.")
        f = request.FILES.get("file") or request.FILES.get("image")
        if not f:
            raise ValidationError({"file": "A file is required."})
        validate_upload(f, allowed_types={"jpg", "jpeg", "png", "webp"})
        img = ComplaintImage.objects.create(
            complaint=c, file=f,
            caption=request.data.get("caption", ""),
            uploaded_by=request.user,
            metadata={"content_type": f.content_type},
        )
        return success(
            ComplaintImageSerializer(img).data,
            "Image uploaded.",
            201,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsOfficerOrAdmin])
    def assign(self, request, pk=None):
        return self._assign(request, False, pk)

    @action(detail=True, methods=["post"], permission_classes=[IsOfficerOrAdmin])
    def reassign(self, request, pk=None):
        return self._assign(request, True, pk)

    @action(detail=True, methods=["post"], permission_classes=[IsOfficerOrAdmin])
    @transaction.atomic
    def unassign(self, request, pk=None):
        complaint = self.get_object()
        assignment = ComplaintAssignment.objects.select_for_update().filter(
            complaint=complaint,
            completed_time__isnull=True,
        ).first()
        if not assignment:
            raise ValidationError({"detail": "Complaint has no active engineer assignment."})
        from django.utils import timezone
        assignment.completed_time = timezone.now()
        assignment.unassigned_at = assignment.completed_time
        assignment.remarks = request.data.get("remarks", "Unassigned by officer.")
        assignment.save(update_fields=["completed_time", "unassigned_at", "remarks"])
        from apps.accounts.models import EngineerProfile
        engineer_profile = EngineerProfile.objects.filter(user=assignment.engineer).first()
        if engineer_profile:
            engineer_profile.workload = max(0, engineer_profile.workload - 1)
            engineer_profile.save(update_fields=["workload"])
        complaint.assigned_engineer = None
        complaint.save(update_fields=["assigned_engineer", "updated_at"])
        if complaint.status in ("ASSIGNED", "IN_PROGRESS", "ON_HOLD"):
            transition(
                complaint,
                "REOPENED",
                request.user,
                assignment.remarks,
                request.META.get("REMOTE_ADDR"),
            )
        from apps.notifications.services import create_notification
        from apps.audit.services import record_audit
        create_notification(
            recipient=assignment.engineer,
            title="Complaint unassigned",
            message=f"Complaint {complaint.id} is no longer assigned to you.",
            notification_type="complaint",
            related_object_type="complaint",
            related_object_id=complaint.pk,
        )
        record_audit(
            actor=request.user,
            action="COMPLAINT_UNASSIGNED",
            entity_type="complaint",
            entity_id=complaint.pk,
            old_value={"engineer_id": assignment.engineer_id},
            new_value={"engineer_id": None},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success(ComplaintSerializer(complaint).data, "Complaint unassigned.")

    @transaction.atomic
    def _assign(self, request, is_reassign, pk):
        from apps.accounts.models import EngineerProfile
        c = self.get_object()
        engineer_id = request.data.get("engineer_id")
        if not engineer_id:
            raise ValidationError({"engineer_id": "This field is required."})
        eng = get_object_or_404(request.user.__class__, pk=engineer_id, role="ENGINEER")
        ep = EngineerProfile.objects.filter(
            user=eng, department_id=c.department_id, available=True,
        ).first()
        if not ep:
            raise ValidationError({"engineer_id": "Engineer must be available in the complaint department."})
        existing = ComplaintAssignment.objects.filter(complaint=c, completed_time__isnull=True).first()
        if not is_reassign and c.status not in ("CLASSIFIED", "REOPENED"):
            raise ValidationError({"status": "Complaint must be classified before assignment."})
        if is_reassign and c.status not in ("ASSIGNED", "IN_PROGRESS", "ON_HOLD", "REOPENED"):
            raise ValidationError({"status": "Complaint is not in an assignable state."})
        if not is_reassign and existing:
            raise ValidationError({
                "detail": "Complaint already assigned; use reassign."
            })
        if is_reassign and existing:
            from django.utils import timezone
            existing.completed_time = timezone.now()
            existing.unassigned_at = existing.completed_time
            existing.remarks = request.data.get("remarks", "Reassigned by officer.")
            existing.save(update_fields=["completed_time", "unassigned_at", "remarks"])
            old_profile = EngineerProfile.objects.filter(user=existing.engineer).first()
            if old_profile:
                old_profile.workload = max(0, old_profile.workload - 1)
                old_profile.save(update_fields=["workload"])
        ComplaintAssignment.objects.create(
            complaint=c, engineer=eng, assigned_by=request.user,
            remarks=request.data.get("remarks", ""),
        )
        c.assigned_engineer = eng
        c.save(update_fields=["assigned_engineer", "updated_at"])
        ep.workload += 1
        ep.save(update_fields=["workload"])
        if c.status in ("CLASSIFIED", "REOPENED"):
            transition(c, "ASSIGNED", request.user, "Assigned to engineer.", request.META.get("REMOTE_ADDR"))
        from apps.notifications.services import create_notification
        from apps.audit.services import record_audit

        create_notification(
            recipient=eng,
            title="Complaint assigned",
            message=f"Complaint {c.id} has been assigned to you.",
            notification_type="complaint",
            related_object_type="complaint",
            related_object_id=c.pk,
        )
        record_audit(
            actor=request.user,
            action="COMPLAINT_REASSIGNED" if is_reassign else "COMPLAINT_ASSIGNED",
            entity_type="complaint",
            entity_id=c.pk,
            old_value={"engineer_id": existing.engineer_id} if is_reassign and existing else None,
            new_value={"engineer_id": eng.id},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success(ComplaintSerializer(c).data, "Complaint assigned.")

    @action(
        detail=True,
        methods=["patch"],
        url_path="status",
        permission_classes=[IsEngineerOfficerOrAdmin],
    )
    @transaction.atomic
    def update_status(self, request, pk=None):
        c = self.get_object()
        new_status = request.data.get("status")
        remarks = request.data.get("remarks", "")
        if not new_status:
            raise ValidationError({"status": "This field is required."})
        if request.user.role == "ENGINEER":
            eng_user = request.user
            if c.assigned_engineer_id != eng_user.id:
                raise PermissionDenied(
                    "Engineer may only update status of assigned complaints."
                )
            if new_status not in ("IN_PROGRESS", "ON_HOLD"):
                raise PermissionDenied("Engineers may only start work or place assigned work on hold.")
        if new_status == "CLASSIFIED":
            if request.user.role not in ("OFFICER", "ADMINISTRATOR"):
                raise PermissionDenied("Only officers may classify complaints.")
            category = request.data.get("category")
            priority = request.data.get("priority", c.priority)
            department_id = request.data.get("department_id", c.department_id)
            if not category:
                raise ValidationError({"category": "Manual classification requires a category."})
            if category not in Complaint.Category.values:
                raise ValidationError({"category": "Invalid complaint category."})
            if priority not in Complaint.Priority.values:
                raise ValidationError({"priority": "Invalid complaint priority."})
            if not department_id:
                raise ValidationError({"department_id": "Manual classification requires a department."})
            from apps.departments.models import Department
            department = get_object_or_404(Department, pk=department_id, active=True)
            old_values = {"category": c.category, "priority": c.priority, "department_id": c.department_id}
            c.category = category
            c.priority = priority
            c.department = department
            c.save(update_fields=["category", "priority", "department", "updated_at"])
            from apps.audit.services import record_audit
            record_audit(
                actor=request.user,
                action="COMPLAINT_CLASSIFIED",
                entity_type="complaint",
                entity_id=c.pk,
                old_value=old_values,
                new_value={"category": category, "priority": priority, "department_id": department.id},
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        transition(c, new_status, request.user, remarks, request.META.get("REMOTE_ADDR"))
        return success(ComplaintSerializer(c).data, "Status updated.")

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsEngineerOnly],
    )
    @transaction.atomic
    def resolution(self, request, pk=None):
        c = self.get_object()
        if c.assigned_engineer_id != request.user.id:
            raise PermissionDenied("Only the assigned engineer may submit resolution.")
        description = request.data.get("description", "")
        if not description.strip():
            raise ValidationError({"description": "A resolution description is required."})
        if c.status != "IN_PROGRESS":
            from .services import InvalidStatusTransition
            raise InvalidStatusTransition("Only in-progress complaints can receive a resolution.")
        evidence = request.FILES.get("evidence") or None
        if evidence:
            validate_upload(evidence)
        resolution = ComplaintResolution.objects.create(
            complaint=c,
            description=description,
            evidence_image=evidence,
            submitted_by=request.user,
        )
        c.resolution_description = description
        c.save(update_fields=["resolution_description", "updated_at"])
        transition(c, "RESOLUTION_SUBMITTED", request.user, "Resolution submitted.", request.META.get("REMOTE_ADDR"))
        transition(c, "VERIFICATION_PENDING", request.user, "Awaiting verification.", request.META.get("REMOTE_ADDR"))
        from apps.audit.services import record_audit
        record_audit(
            actor=request.user,
            action="RESOLUTION_SUBMITTED",
            entity_type="complaint_resolution",
            entity_id=resolution.pk,
            new_value={"complaint_id": c.pk, "description": description},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success(ComplaintSerializer(c).data, "Resolution submitted.")

    @action(
        detail=True,
        methods=["post"],
        url_path="verify-resolution",
        permission_classes=[IsOfficerOnly],
    )
    @transaction.atomic
    def verify_resolution(self, request, pk=None):
        c = self.get_object()
        approved = request.data.get("approved")
        remarks = request.data.get("remarks", "")
        if approved is None:
            raise ValidationError({"approved": "This field is required."})
        if not isinstance(approved, bool):
            raise ValidationError({"approved": "This field must be true or false."})
        resolution = c.resolutions.first()
        if not resolution:
            raise ValidationError({"detail": "No resolution has been submitted for this complaint."})
        if c.status != "VERIFICATION_PENDING":
            from .services import InvalidStatusTransition
            raise InvalidStatusTransition("Complaint is not awaiting resolution verification.")
        if approved:
            transition(c, "RESOLVED", request.user, remarks or "Resolution verified and approved.", request.META.get("REMOTE_ADDR"))
            resolution.verification_status = ComplaintResolution.VerificationStatus.APPROVED
        else:
            transition(c, "REOPENED", request.user, remarks or "Verification failed; reopened.", request.META.get("REMOTE_ADDR"))
            resolution.verification_status = ComplaintResolution.VerificationStatus.REJECTED
        from django.utils import timezone
        resolution.verified_by = request.user
        resolution.verified_at = timezone.now()
        resolution.verification_remarks = remarks
        resolution.save(update_fields=["verification_status", "verified_by", "verified_at", "verification_remarks"])
        from apps.audit.services import record_audit
        record_audit(
            actor=request.user,
            action="RESOLUTION_VERIFIED",
            entity_type="complaint_resolution",
            entity_id=resolution.pk,
            old_value={"verification_status": ComplaintResolution.VerificationStatus.PENDING},
            new_value={"verification_status": resolution.verification_status, "remarks": remarks},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success(ComplaintSerializer(c).data, "Resolution verified.")

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def feedback(self, request, pk=None):
        c = self.get_object()
        if c.citizen_id != request.user.id:
            raise PermissionDenied("Only the reporting citizen may submit feedback.")
        if c.status not in (Complaint.Status.RESOLVED, Complaint.Status.CLOSED):
            raise ValidationError(
                {"detail": "Feedback may only be submitted for resolved or closed complaints."}
            )
        if hasattr(c, "feedback") and c.feedback is not None:
            raise ValidationError({"detail": "Feedback has already been submitted."})
        s = ComplaintFeedbackSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        o = ComplaintFeedback.objects.create(
            complaint=c, citizen=request.user, **s.validated_data,
        )
        from apps.audit.services import record_audit
        record_audit(
            actor=request.user,
            action="COMPLAINT_FEEDBACK_SUBMITTED",
            entity_type="complaint",
            entity_id=c.pk,
            new_value={"rating": o.rating},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        if c.status == Complaint.Status.RESOLVED:
            transition(c, Complaint.Status.CLOSED, request.user, "Complaint closed after citizen feedback.", request.META.get("REMOTE_ADDR"))
        return success(
            ComplaintFeedbackSerializer(o).data,
            "Feedback submitted.",
            200,
        )

    @action(detail=True, methods=["get"], url_path="ai")
    def ai_result(self, request, pk=None):
        c = self.get_object()
        user = request.user
        is_owner = c.citizen_id == user.id
        if not (is_owner or user.role in ("OFFICER", "ENGINEER", "ADMINISTRATOR")):
            raise PermissionDenied()
        latest = c.ai_analyses.first()
        if not latest:
            return success(None)
        return success(AIAnalysisSerializer(latest).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="ai/analyze",
        permission_classes=[IsOfficerEngineer],
    )
    def ai_analyze(self, request, pk=None):
        from apps.ai.services import analyze_complaint
        c = self.get_object()
        result = analyze_complaint(
            c, actor=request.user, ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success(result, result["message"], 200)

    @action(
        detail=True,
        methods=["patch"],
        url_path="ai-review",
        permission_classes=[IsOfficerEngineer],
    )
    def ai_review(self, request, pk=None):
        c = self.get_object()
        a = c.ai_analyses.order_by("-created_at").first()
        if not a:
            raise ValidationError({"detail": "No AI analysis exists."})
        override_cat = request.data.get("category")
        override_pri = request.data.get("priority")
        override_dept_id = request.data.get("department_id") or request.data.get("department")
        override_dept = None
        if override_dept_id:
            from apps.departments.models import Department
            override_dept = get_object_or_404(Department, pk=override_dept_id)
        a.human_category = override_cat or a.human_category
        a.human_priority = override_pri or a.human_priority
        if override_dept:
            a.human_department = override_dept
        a.reviewed_by = request.user
        from django.utils import timezone
        a.reviewed_at = timezone.now()
        a.is_overridden = True
        a.review_remarks = request.data.get("remarks", a.review_remarks)
        a.save()
        if a.human_category:
            c.category = a.human_category
        if a.human_priority:
            c.priority = a.human_priority
        if a.human_department_id:
            c.department_id = a.human_department_id
        c.save(update_fields=["category", "priority", "department_id", "updated_at"])
        return success(AIAnalysisSerializer(a).data, "AI recommendation reviewed.")

    @action(
        detail=True,
        methods=["post"],
        url_path="ai/accept",
        permission_classes=[IsOfficerOrAdmin],
    )
    @transaction.atomic
    def ai_accept(self, request, pk=None):
        """Accept the latest AI recommendation and classify the complaint.

        This is the fast path for the officer: it copies the (validated) AI
        category/priority/department onto the complaint and advances it to
        CLASSIFIED, recording the human decision as a non-override.
        """
        from django.utils import timezone
        c = self.get_object()
        a = c.ai_analyses.order_by("-created_at").first()
        if not a:
            raise ValidationError({"detail": "No AI analysis exists to accept."})
        category = a.category_prediction
        department = a.department_recommendation
        priority = a.priority_prediction or c.priority
        if not category:
            raise ValidationError(
                {"detail": "AI produced no category; classify the complaint manually."}
            )
        if not department:
            raise ValidationError(
                {"detail": "No active department mapping for the predicted category; "
                           "classify the complaint manually."}
            )
        old_values = {
            "category": c.category,
            "priority": c.priority,
            "department_id": c.department_id,
        }
        c.category = category
        c.priority = priority
        c.department = department
        c.save(update_fields=["category", "priority", "department", "updated_at"])

        a.human_category = category
        a.human_priority = priority
        a.human_department = department
        a.reviewed_by = request.user
        a.reviewed_at = timezone.now()
        a.is_overridden = False
        a.review_remarks = request.data.get("remarks", "AI recommendation accepted.")
        a.save()

        from apps.audit.services import record_audit
        record_audit(
            actor=request.user,
            action="AI_RECOMMENDATION_ACCEPTED",
            entity_type="complaint",
            entity_id=c.pk,
            old_value=old_values,
            new_value={
                "category": category,
                "priority": priority,
                "department_id": department.id,
            },
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        if c.status in (Complaint.Status.SUBMITTED, Complaint.Status.AI_PROCESSING):
            transition(
                c,
                Complaint.Status.CLASSIFIED,
                request.user,
                "AI recommendation accepted.",
                request.META.get("REMOTE_ADDR"),
            )
        return success(AIAnalysisSerializer(a).data, "AI recommendation accepted.")
