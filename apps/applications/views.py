import datetime as _dt
from collections import defaultdict
from io import BytesIO
from xml.sax.saxutils import escape
from django.db import models
from django.db import transaction
from django.db.models import Count, Max
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status as http_status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_field
from common.permissions import IsOfficerOrAdmin, IsAdministrator
from common.responses import success
from common.pagination import paginated_success
from apps.complaints.validators import validate_upload
from .models import (
    BusinessApplication, ApplicationDocument, ApplicationStatusHistory,
    ApplicationEngineerAssignment,
)

_STATUS_TRANSITIONS = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"UNDER_REVIEW", "CLARIFICATION_REQUIRED", "CLARIFICATION_REQUESTED", "CANCELLED"},
    "UNDER_REVIEW": {"DOCUMENT_VERIFICATION", "ENGINEER_REVIEW", "FIELD_VERIFICATION", "CLARIFICATION_REQUIRED", "CLARIFICATION_REQUESTED", "APPROVED", "REJECTED"},
    "DOCUMENT_VERIFICATION": {"UNDER_REVIEW", "ENGINEER_REVIEW", "FIELD_VERIFICATION", "CLARIFICATION_REQUIRED", "CLARIFICATION_REQUESTED", "APPROVED", "REJECTED"},
    "ENGINEER_REVIEW": {"UNDER_REVIEW", "FIELD_VERIFICATION", "CLARIFICATION_REQUIRED", "CLARIFICATION_REQUESTED"},
    "FIELD_VERIFICATION": {"UNDER_REVIEW", "ENGINEER_REVIEW", "DOCUMENT_VERIFICATION", "CLARIFICATION_REQUIRED", "CLARIFICATION_REQUESTED", "APPROVED", "REJECTED"},
    "CLARIFICATION_REQUIRED": {"UNDER_REVIEW", "DOCUMENT_VERIFICATION", "APPROVED", "REJECTED", "CANCELLED"},
    "CLARIFICATION_REQUESTED": {"UNDER_REVIEW", "DOCUMENT_VERIFICATION", "CLARIFICATION_REQUIRED", "APPROVED", "REJECTED", "CANCELLED"},
    "APPROVED": {"COMPLETED"},
    "REJECTED": set(),
    "COMPLETED": set(),
    "CANCELLED": set(),
}


class InvalidApplicationStatus(ValidationError):
    pass


_ACTIVE_REVIEW_STATUSES = (
    "SUBMITTED", "UNDER_REVIEW", "DOCUMENT_VERIFICATION", "ENGINEER_REVIEW", "FIELD_VERIFICATION",
    "CLARIFICATION_REQUIRED", "CLARIFICATION_REQUESTED",
)


@transaction.atomic
def _status_change(application, new_status, user, remarks="", ip_address=None):
    current = BusinessApplication.objects.select_for_update().get(pk=application.pk)
    if new_status not in _STATUS_TRANSITIONS.get(current.status, set()):
        from apps.complaints.services import InvalidStatusTransition
        raise InvalidStatusTransition(
            f"Transition from {current.status} to {new_status} is not allowed."
        )
    old = current.status
    current.status = new_status
    current.save(update_fields=["status", "updated_at"])
    application.status = current.status
    application.updated_at = current.updated_at
    ApplicationStatusHistory.objects.create(
        application=application,
        old_status=old,
        new_status=new_status,
        changed_by=user,
        remarks=remarks,
    )
    from apps.notifications.services import create_notification
    from apps.audit.services import record_audit

    event_action = {
        "UNDER_REVIEW": "APPLICATION_REVIEWED",
        "APPROVED": "APPLICATION_APPROVED",
        "REJECTED": "APPLICATION_REJECTED",
        "COMPLETED": "APPLICATION_COMPLETED",
    }.get(new_status, "APPLICATION_STATUS_CHANGED")
    create_notification(
        recipient=application.applicant,
        title="Application status updated",
        message=f"Application {application.application_number} is now {new_status.replace('_', ' ').lower()}.",
        notification_type="application",
        related_object_type="application",
        related_object_id=application.pk,
    )
    record_audit(
        actor=user,
        action=event_action,
        entity_type="application",
        entity_id=application.pk,
        old_value={"status": old},
        new_value={"status": new_status, "remarks": remarks},
        ip_address=ip_address,
    )
    return application

def _ensure_initial_history(application):
    if not application.history.exists():
        ApplicationStatusHistory.objects.create(
            application=application,
            old_status="",
            new_status=application.status,
            changed_by=application.applicant,
            remarks="Application submitted.",
        )


def _generate_application_number(year=None):
    year = year or _dt.date.today().year
    prefix = f"MUN-{year}-"
    last = (
        BusinessApplication.objects
        .filter(application_number__startswith=prefix)
        .aggregate(m=Max("application_number"))
        .get("m")
    )
    seq = 1000
    if last:
        try:
            seq = int(last.rsplit("-", 1)[-1]) + 1
        except Exception:
            pass
    return f"{prefix}{seq}"


@transaction.atomic
def _auto_assign_officer(application):
    from apps.accounts.models import OfficerProfile

    current = application.assigned_officer
    if current and current.available and current.user.is_active and current.department_id == application.department_id:
        return current

    officers = list(
        OfficerProfile.objects.select_for_update()
        .filter(department_id=application.department_id, available=True, user__is_active=True)
        .select_related("user")
        .order_by("id")
    )
    if not officers:
        application.assigned_officer = None
        application.save(update_fields=["assigned_officer", "updated_at"])
        return None

    workloads = defaultdict(int)
    rows = (
        BusinessApplication.objects.filter(
            assigned_officer_id__in=[officer.id for officer in officers],
            status__in=_ACTIVE_REVIEW_STATUSES,
        )
        .exclude(pk=application.pk)
        .values("assigned_officer_id")
        .annotate(total=Count("id"))
    )
    for row in rows:
        workloads[row["assigned_officer_id"]] = row["total"]

    assigned = min(officers, key=lambda officer: (workloads[officer.id], officer.id))
    application.assigned_officer = assigned
    application.save(update_fields=["assigned_officer", "updated_at"])
    from apps.notifications.services import create_notification
    create_notification(
        recipient=assigned.user,
        title="Application assigned",
        message=f"Application {application.application_number} was assigned to your department review queue.",
        notification_type="application",
        related_object_type="application",
        related_object_id=application.pk,
    )
    return assigned


class DocumentSerializer(ModelSerializer):
    download_url = SerializerMethodField()

    class Meta:
        model = ApplicationDocument
        fields = (
            "id", "key", "label", "filename", "uploaded_at", "status",
            "remarks", "verified_by", "verified_at", "download_url",
        )
        read_only_fields = ("id", "uploaded_at", "verified_by", "verified_at")

    def get_download_url(self, obj):
        request = self.context.get("request")
        path = f"/api/v1/applications/{obj.application_id}/documents/{obj.id}/download/"
        return request.build_absolute_uri(path) if request else path


class ApplicationSerializer(ModelSerializer):
    service = SerializerMethodField()
    department = SerializerMethodField()
    assigned_officer = SerializerMethodField()
    applicant_name = SerializerMethodField()
    business_id = SerializerMethodField()
    business_name = SerializerMethodField()
    assigned_engineer = SerializerMethodField()
    documents = DocumentSerializer(many=True, read_only=True)
    timeline = SerializerMethodField()
    data = SerializerMethodField()

    class Meta:
        model = BusinessApplication
        fields = (
            "id", "application_number",
            "service", "department",
            "status", "applicant_name",
            "business_id", "business_name", "rejection_reason", "remarks",
            "assigned_engineer",
            "submitted_at", "updated_at",
            "assigned_officer",
            "data",
            "documents",
            "timeline",
        )
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_service(self, obj):
        if not obj.service_id:
            return None
        return {
            "id": obj.service_id,
            "name": obj.service.name,
            "code": obj.service.code or "",
        }

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_department(self, obj):
        if not obj.department_id:
            return None
        return {"id": obj.department_id, "name": obj.department.name}

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_assigned_officer(self, obj):
        if not obj.assigned_officer_id:
            return None
        return {
            "id": obj.assigned_officer.user_id,
            "name": obj.assigned_officer.user.name,
        }

    @extend_schema_field(OpenApiTypes.STR)
    def get_applicant_name(self, obj):
        return obj.applicant.name if obj.applicant_id else ""

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_business_id(self, obj):
        return obj.business_id

    @extend_schema_field(OpenApiTypes.STR)
    def get_business_name(self, obj):
        return obj.business.name if obj.business_id else ""

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_assigned_engineer(self, obj):
        if not obj.assigned_engineer_id:
            return None
        engineer = obj.assigned_engineer
        return {
            "id": engineer.id,
            "user_id": engineer.user_id,
            "name": engineer.user.name,
            "specialization": engineer.specialization,
        }

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_data(self, obj):
        return obj.data or {}

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_timeline(self, obj):
        out = []
        for h in obj.history.select_related("changed_by").all():
            out.append({
                "status": h.new_status,
                "timestamp": h.timestamp,
                "actor": h.changed_by.name if h.changed_by else "System",
                "remarks": h.remarks or "",
            })
        for assignment in obj.engineer_assignments.select_related(
            "engineer__user", "assigned_by",
        ).all():
            out.append({
                "status": "ENGINEER_ASSIGNED",
                "timestamp": assignment.assigned_at,
                "actor": assignment.assigned_by.name,
                "remarks": assignment.remarks or f"Assigned to {assignment.engineer.user.name}.",
            })
        out.sort(key=lambda event: event["timestamp"])
        return out


class ApplicationCreateSerializer(ModelSerializer):
    service_id = serializers.IntegerField(required=True, write_only=True)
    business_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    data = serializers.JSONField(required=False, default=dict)
    draft = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = BusinessApplication
        fields = ("service_id", "business_id", "data", "draft")


def _missing_required_fields(service, data, uploaded_keys):
    missing = []
    for requirement in service.requirements or []:
        if not requirement.get("required", False):
            continue
        key = requirement.get("key")
        if requirement.get("type") == "file":
            if key not in uploaded_keys:
                missing.append(key)
        elif data.get(key) is None or data.get(key) == "":
            missing.append(key)
    return missing


def _can_view_application(user, app):
    if user.role == "ADMINISTRATOR":
        return True
    if app.applicant_id == user.id:
        return True
    if user.role == "OFFICER" and hasattr(user, "officer_profile"):
        if app.assigned_officer_id == user.officer_profile.id:
            return True
        if (
            app.assigned_officer_id is None
            and app.department_id == user.officer_profile.department_id
            and user.officer_profile.available
        ):
            return True
    if user.role == "ENGINEER" and hasattr(user, "engineer_profile"):
        return app.assigned_engineer_id == user.engineer_profile.id
    return False


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = BusinessApplication.objects.none()
    serializer_class = ApplicationSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return ApplicationCreateSerializer
        return ApplicationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        u = self.request.user
        q = BusinessApplication.objects.select_related(
            "applicant", "service", "department",
            "assigned_officer", "assigned_officer__user",
            "assigned_engineer", "assigned_engineer__user",
        ).prefetch_related(
            "documents", "history", "history__changed_by",
            "engineer_assignments", "engineer_assignments__engineer__user",
            "engineer_assignments__assigned_by",
        )
        if u.role == "ADMINISTRATOR":
            return q
        if u.role == "OFFICER" and hasattr(u, "officer_profile"):
            assigned = q.filter(assigned_officer=u.officer_profile)
            if u.officer_profile.available:
                assigned = assigned | q.filter(
                    department=u.officer_profile.department,
                    assigned_officer__isnull=True,
                    status__in=_ACTIVE_REVIEW_STATUSES,
                )
            return assigned.distinct()
        if u.role == "ENGINEER" and hasattr(u, "engineer_profile"):
            return q.filter(assigned_engineer=u.engineer_profile)
        return q.filter(applicant=u)

    def get_object(self):
        from django.db import models
        obj = super().get_object()
        if not _can_view_application(self.request.user, obj):
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
        status_value = params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        department = params.get("department", params.get("department_id"))
        if department:
            queryset = queryset.filter(department_id=department)
        service = params.get("service", params.get("service_id"))
        if service:
            queryset = queryset.filter(service_id=service)
        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(application_number__icontains=search)
                | models.Q(service__name__icontains=search)
                | models.Q(applicant__name__icontains=search)
            )
        ordering = params.get("ordering", "-submitted_at")
        allowed_ordering = {"submitted_at", "-submitted_at", "updated_at", "-updated_at", "status", "-status"}
        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering, "id")
        return queryset

    def retrieve(self, request, *args, **kwargs):
        return success(self.get_serializer(self.get_object()).data)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if request.user.role not in ("CITIZEN", "BUSINESS_OWNER"):
            raise PermissionDenied(
                "Only citizens and business owners may submit applications."
            )
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        from apps.services.models import Service
        service_id = s.validated_data["service_id"]
        service = get_object_or_404(Service, pk=service_id, active=True)
        business_id = s.validated_data.get("business_id")
        create_as_draft = s.validated_data.get("draft", False)
        business = None
        if business_id:
            from apps.businesses.models import BusinessProfile
            business = get_object_or_404(
                BusinessProfile, pk=business_id, owner=request.user,
            )
        file_uploads = []
        for field_name, uploaded_file in request.FILES.items():
            if not field_name.startswith("document:"):
                raise ValidationError({"file": "Use document:<requirement-key> for application documents."})
            key = field_name.split(":", 1)[1]
            requirement = next(
                (
                    item for item in (service.requirements or [])
                    if item.get("key") == key and item.get("type") == "file"
                ),
                None,
            )
            if not requirement:
                raise ValidationError({"file": f"'{key}' is not a file requirement for this service."})
            document_rule = service.required_documents.filter(key=key).first()
            allowed_types = document_rule.allowed_file_types if document_rule else requirement.get("allowed_file_types", [])
            max_file_size = document_rule.max_file_size if document_rule else requirement.get("max_file_size", 10 * 1024 * 1024)
            validate_upload(uploaded_file, max_size=max_file_size, allowed_types=allowed_types)
            file_uploads.append((key, requirement, uploaded_file))
        data = s.validated_data.get("data", {})
        if not create_as_draft:
            missing = _missing_required_fields(service, data, {key for key, *_ in file_uploads})
            if missing:
                raise ValidationError({"required_fields": {key: "This field is required." for key in missing}})
        app = BusinessApplication.objects.create(
            applicant=request.user,
            service=service,
            business=business,
            application_number=_generate_application_number(),
            department=service.department,
            status=(BusinessApplication.Status.DRAFT if create_as_draft else BusinessApplication.Status.SUBMITTED),
            data=data,
        )
        _ensure_initial_history(app)
        if app.status == BusinessApplication.Status.SUBMITTED:
            _auto_assign_officer(app)
        for key, requirement, uploaded_file in file_uploads:
            document = ApplicationDocument.objects.create(
                application=app,
                key=key,
                label=requirement.get("label", ""),
                filename=uploaded_file.name,
                file=uploaded_file,
                uploaded_by=request.user,
            )
            from apps.audit.services import record_audit
            record_audit(
                actor=request.user,
                action="DOCUMENT_UPLOADED",
                entity_type="application_document",
                entity_id=document.pk,
                new_value={"application_id": app.pk, "key": key, "filename": document.filename},
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        from apps.audit.services import record_audit

        record_audit(
            actor=request.user,
            action="APPLICATION_CREATED" if create_as_draft else "APPLICATION_SUBMITTED",
            entity_type="application",
            entity_id=app.pk,
            new_value={"status": app.status, "application_number": app.application_number},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        if not create_as_draft:
            from apps.notifications.services import create_notification
            create_notification(
                recipient=request.user,
                title="Application submitted",
                message=f"Application {app.application_number} was submitted successfully.",
                notification_type="application",
                related_object_type="application",
                related_object_id=app.pk,
            )
        return success(
            ApplicationSerializer(app).data,
            "Application submitted.",
            201,
        )

    def partial_update(self, request, *args, **kwargs):
        app = self.get_object()
        if app.applicant_id != request.user.id or app.status not in (
            BusinessApplication.Status.DRAFT,
            BusinessApplication.Status.CLARIFICATION_REQUIRED,
            BusinessApplication.Status.CLARIFICATION_REQUESTED,
        ):
            raise PermissionDenied("Only the applicant may update a draft or respond to clarification.")
        data = request.data.get("data")
        if not isinstance(data, dict):
            raise ValidationError({"data": "Provide application data as an object."})
        old_data = app.data
        app.data = {**(app.data or {}), **data}
        app.save(update_fields=["data", "updated_at"])
        from apps.audit.services import record_audit
        record_audit(
            actor=request.user,
            action="APPLICATION_UPDATED",
            entity_type="application",
            entity_id=app.pk,
            old_value={"data": old_data},
            new_value={"data": app.data},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success(self.get_serializer(app).data, "Application information updated.")

    def update(self, request, *args, **kwargs):
        raise PermissionDenied("Direct update of application fields is not allowed; use workflow endpoints.")

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("Applications may not be deleted.")

    @action(detail=True, methods=["get"])
    def documents(self, request, pk=None):
        app = self.get_object()
        return success(
            DocumentSerializer(app.documents.all(), many=True).data
        )

    @action(
        detail=True,
        methods=["get"],
        url_path=r"documents/(?P<document_id>[^/.]+)/download",
    )
    def download_document(self, request, pk=None, document_id=None):
        app = self.get_object()
        document = get_object_or_404(app.documents, pk=document_id)
        if not document.file:
            raise ValidationError({"file": "This document has no stored file."})
        return FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=document.filename or document.file.name.rsplit("/", 1)[-1],
        )

    @action(detail=True, methods=["get"])
    def certificate(self, request, pk=None):
        app = self.get_object()
        if app.status not in (BusinessApplication.Status.APPROVED, BusinessApplication.Status.COMPLETED):
            raise ValidationError({"status": "A certificate is available only after approval."})

        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        buffer = BytesIO()
        pdf = SimpleDocTemplate(buffer, pagesize=A4, title=f"Approval {app.application_number}")
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="ApprovalCertificateTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0e4f63"),
        ))

        def paragraph(value):
            safe_value = escape(str(value)).encode("ascii", "ignore").decode("ascii")
            return Paragraph(safe_value, styles["BodyText"])

        story = [
            Paragraph("Municipal Service Approval", styles["ApprovalCertificateTitle"]),
            Spacer(1, 18),
            paragraph("This document records approval of the service application below."),
            Spacer(1, 18),
        ]
        rows = [
            ("Application number", app.application_number),
            ("Service", app.service.name),
            ("Department", app.department.name),
            ("Applicant", app.applicant.name),
            ("Business", app.business.name if app.business_id else "Not specified"),
            ("Decision", "APPROVED"),
            ("Decision date", app.updated_at.strftime("%d %B %Y")),
        ]
        table = Table(
            [[paragraph(key), paragraph(value)] for key, value in rows],
            colWidths=[145, 330],
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f3f5")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b7c9ce")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.extend([
            table,
            Spacer(1, 22),
            Paragraph(
                "Digitally generated record from the municipal service portal.",
                styles["Italic"],
            ),
        ])
        pdf.build(story)
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="approval-{app.application_number}.pdf"'
        return response

    @documents.mapping.post
    @transaction.atomic
    def upload_document(self, request, pk=None):
        app = self.get_object()
        if app.applicant_id != request.user.id:
            raise PermissionDenied("Only the applicant may upload documents.")
        if app.status not in (
            BusinessApplication.Status.DRAFT,
            BusinessApplication.Status.SUBMITTED,
            BusinessApplication.Status.CLARIFICATION_REQUIRED,
            BusinessApplication.Status.CLARIFICATION_REQUESTED,
        ):
            raise PermissionDenied("Documents cannot be uploaded in the current application state.")
        f = request.FILES.get("file")
        if not f:
            raise ValidationError({"file": "A file is required."})
        validate_upload(f, max_size=10 * 1024 * 1024)
        key = request.data.get("key", "")
        label = request.data.get("label", "")
        configured_document = app.service.required_documents.filter(key=key).first()
        legacy_requirement = next(
            (
                item for item in (app.service.requirements or [])
                if item.get("key") == key and item.get("type") == "file"
            ),
            None,
        )
        configured_file_keys = {
            item.get("key") for item in (app.service.requirements or [])
            if item.get("type") == "file"
        }
        if configured_file_keys and not configured_document and not legacy_requirement:
            raise ValidationError({"key": "This document is not required by the selected service."})
        if configured_document:
            allowed_types = configured_document.allowed_file_types
            max_file_size = configured_document.max_file_size
            label = label or configured_document.name
        elif legacy_requirement:
            allowed_types = legacy_requirement.get("allowed_file_types", [])
            max_file_size = legacy_requirement.get("max_file_size", 10 * 1024 * 1024)
            label = label or legacy_requirement.get("label", "")
        else:
            allowed_types = []
            max_file_size = 10 * 1024 * 1024
        validate_upload(f, max_size=max_file_size, allowed_types=allowed_types)
        if app.service_id:
            for req in (app.service.requirements or []):
                if req.get("key") == key:
                    label = label or req.get("label", "")
                    break
        doc = ApplicationDocument.objects.create(
            application=app,
            file=f,
            key=key,
            label=label,
            filename=getattr(f, "name", ""),
            uploaded_by=request.user,
        )
        from apps.audit.services import record_audit

        record_audit(
            actor=request.user,
            action="DOCUMENT_UPLOADED",
            entity_type="application_document",
            entity_id=doc.pk,
            new_value={"application_id": app.pk, "key": key, "filename": doc.filename},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success(
            DocumentSerializer(doc).data,
            "Document uploaded.",
            201,
        )

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        app = self.get_object()
        out = []
        for h in app.history.select_related("changed_by").all():
            out.append({
                "status": h.new_status,
                "timestamp": h.timestamp,
                "actor": h.changed_by.name if h.changed_by else "System",
                "remarks": h.remarks or "",
            })
        return success(out)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    @transaction.atomic
    def submit(self, request, pk=None):
        app = self.get_object()
        if app.applicant_id != request.user.id:
            raise PermissionDenied("Only the applicant may submit this application.")
        if app.status == BusinessApplication.Status.DRAFT:
            new_status = BusinessApplication.Status.SUBMITTED
            remarks = "Application submitted by applicant."
        elif app.status in (
            BusinessApplication.Status.CLARIFICATION_REQUIRED,
            BusinessApplication.Status.CLARIFICATION_REQUESTED,
        ):
            new_status = BusinessApplication.Status.UNDER_REVIEW
            remarks = "Applicant responded to requested clarification."
        else:
            raise ValidationError({"status": "Application is not awaiting applicant submission."})

        uploaded_keys = set(app.documents.values_list("key", flat=True))
        missing = _missing_required_fields(app.service, app.data or {}, uploaded_keys)
        if missing:
            raise ValidationError({"required_fields": {key: "This field is required." for key in missing}})

        _status_change(
            app,
            new_status,
            request.user,
            remarks,
            request.META.get("REMOTE_ADDR"),
        )
        _auto_assign_officer(app)
        return success(self.get_serializer(app).data, "Application submitted.")

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    @transaction.atomic
    def cancel(self, request, pk=None):
        app = self.get_object()
        if app.applicant_id != request.user.id:
            raise PermissionDenied("Only the applicant may cancel this application.")
        _status_change(
            app,
            BusinessApplication.Status.CANCELLED,
            request.user,
            request.data.get("remarks", "Cancelled by applicant."),
            request.META.get("REMOTE_ADDR"),
        )
        return success(self.get_serializer(app).data, "Application cancelled.")

    @action(
        detail=True,
        methods=["patch"],
        url_path=r"documents/(?P<document_id>[^/.]+)/verify",
        permission_classes=[IsOfficerOrAdmin],
    )
    @extend_schema(parameters=[OpenApiParameter("document_id", OpenApiTypes.INT, OpenApiParameter.PATH)])
    @transaction.atomic
    def verify_document(self, request, pk=None, document_id=None):
        app = self.get_object()
        document = get_object_or_404(app.documents, pk=document_id)
        status_value = request.data.get("status")
        if status_value not in ApplicationDocument.DocStatus.values:
            raise ValidationError({"status": "Status must be PENDING, VERIFIED, or REJECTED."})
        document.status = status_value
        document.remarks = request.data.get("remarks", "")
        document.verified_by = request.user
        from django.utils import timezone
        document.verified_at = timezone.now()
        document.save(update_fields=["status", "remarks", "verified_by", "verified_at"])
        if app.status == BusinessApplication.Status.UNDER_REVIEW:
            _status_change(
                app,
                BusinessApplication.Status.DOCUMENT_VERIFICATION,
                request.user,
                "Document verification started.",
                request.META.get("REMOTE_ADDR"),
            )
        from apps.notifications.services import create_notification
        from apps.audit.services import record_audit
        create_notification(
            recipient=app.applicant,
            title="Application document reviewed",
            message=f"Document {document.label or document.key} was marked {status_value.lower()}.",
            notification_type="application",
            related_object_type="application",
            related_object_id=app.pk,
        )
        record_audit(
            actor=request.user,
            action="DOCUMENT_VERIFIED",
            entity_type="application_document",
            entity_id=document.pk,
            new_value={"status": status_value, "remarks": document.remarks},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success(DocumentSerializer(document).data, "Application document reviewed.")

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
    )
    def assigned(self, request):
        u = request.user
        qs = self.get_queryset()
        if u.role == "OFFICER" and hasattr(u, "officer_profile"):
            qs = qs.filter(assigned_officer=u.officer_profile)
            if u.officer_profile.available:
                qs = qs | self.get_queryset().filter(
                    assigned_officer__isnull=True,
                    department=u.officer_profile.department,
                    status__in=_ACTIVE_REVIEW_STATUSES,
                )
        elif u.role == "ENGINEER" and hasattr(u, "engineer_profile"):
            qs = qs.filter(assigned_engineer=u.engineer_profile)
        elif u.role != "ADMINISTRATOR":
            raise PermissionDenied("Only officers, engineers, and administrators may view the service queue.")
        return success(
            self.get_serializer(qs, many=True).data
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="eligible-engineers",
        permission_classes=[IsAuthenticated],
    )
    def eligible_engineers(self, request, pk=None):
        app = self.get_object()
        if request.user.role == "OFFICER":
            profile = getattr(request.user, "officer_profile", None)
            if not profile or profile.department_id != app.department_id:
                raise PermissionDenied("Only the department officer may assign an engineer.")
            if app.assigned_officer_id and app.assigned_officer_id != profile.id:
                raise PermissionDenied("This application is assigned to another officer.")
        elif request.user.role != "ADMINISTRATOR":
            raise PermissionDenied("Only officers and administrators may select an engineer.")

        from apps.accounts.models import EngineerProfile
        workload = Count(
            "assigned_applications",
            filter=models.Q(assigned_applications__status__in=_ACTIVE_REVIEW_STATUSES),
        )
        engineers = EngineerProfile.objects.filter(
            department_id=app.department_id,
            available=True,
            user__is_active=True,
            services=app.service,
        ).annotate(active_workload=workload).select_related("user").order_by("active_workload", "id")
        return success([
            {
                "id": engineer.id,
                "user_id": engineer.user_id,
                "name": engineer.user.name,
                "specialization": engineer.specialization,
                "workload": engineer.active_workload,
            }
            for engineer in engineers.distinct()
        ])

    @action(
        detail=True,
        methods=["post"],
        url_path="assign-engineer",
        permission_classes=[IsAuthenticated],
    )
    @transaction.atomic
    def assign_engineer(self, request, pk=None):
        app = self.get_object()
        if request.user.role == "OFFICER":
            profile = getattr(request.user, "officer_profile", None)
            if not profile or profile.department_id != app.department_id:
                raise PermissionDenied("Only the department officer may assign an engineer.")
            if not profile.available:
                raise PermissionDenied("Only the available department officer may assign an engineer.")
            if app.assigned_officer_id and app.assigned_officer_id != profile.id:
                raise PermissionDenied("This application is assigned to another officer.")
        elif request.user.role != "ADMINISTRATOR":
            raise PermissionDenied("Only officers and administrators may assign an engineer.")

        if app.status not in (
            BusinessApplication.Status.UNDER_REVIEW,
            BusinessApplication.Status.DOCUMENT_VERIFICATION,
            BusinessApplication.Status.ENGINEER_REVIEW,
            BusinessApplication.Status.FIELD_VERIFICATION,
        ):
            raise ValidationError({"status": "The application must be under officer review before engineer assignment."})

        engineer_id = request.data.get("engineer_profile_id")
        from apps.accounts.models import EngineerProfile
        engineer = EngineerProfile.objects.filter(
            pk=engineer_id,
            department_id=app.department_id,
            available=True,
            user__is_active=True,
            services=app.service,
        ).select_related("user").first()
        if not engineer:
            raise ValidationError({"engineer_profile_id": "Choose an available engineer qualified for this service and department."})

        from django.utils import timezone
        active_assignment = app.engineer_assignments.filter(unassigned_at__isnull=True).first()
        if active_assignment and active_assignment.engineer_id != engineer.id:
            active_assignment.unassigned_at = timezone.now()
            active_assignment.save(update_fields=["unassigned_at"])

        ApplicationEngineerAssignment.objects.create(
            application=app,
            engineer=engineer,
            assigned_by=request.user,
            remarks=request.data.get("remarks", "Assigned by department officer."),
        )
        app.assigned_engineer = engineer
        app.save(update_fields=["assigned_engineer", "updated_at"])

        target_status = (
            BusinessApplication.Status.FIELD_VERIFICATION
            if app.service.field_verification_required
            else BusinessApplication.Status.ENGINEER_REVIEW
        )
        if app.status != target_status:
            _status_change(
                app,
                target_status,
                request.user,
                request.data.get("remarks", f"Assigned to {engineer.user.name} for service review."),
                request.META.get("REMOTE_ADDR"),
            )
        from apps.notifications.services import create_notification
        from apps.audit.services import record_audit
        create_notification(
            recipient=engineer.user,
            title="Service application assigned",
            message=f"Application {app.application_number} for {app.service.name} was assigned to you.",
            notification_type="application",
            related_object_type="application",
            related_object_id=app.pk,
        )
        record_audit(
            actor=request.user,
            action="APPLICATION_ENGINEER_ASSIGNED",
            entity_type="application",
            entity_id=app.pk,
            old_value={"engineer_profile_id": active_assignment.engineer_id if active_assignment else None},
            new_value={"engineer_profile_id": engineer.id, "service_id": app.service_id},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success(self.get_serializer(app).data, "Engineer assigned to service application.")

    @action(
        detail=True,
        methods=["post"],
        url_path="complete-engineer-review",
        permission_classes=[IsAuthenticated],
    )
    @transaction.atomic
    def complete_engineer_review(self, request, pk=None):
        app = self.get_object()
        profile = getattr(request.user, "engineer_profile", None)
        if request.user.role != "ENGINEER" or not profile or app.assigned_engineer_id != profile.id:
            raise PermissionDenied("Only the assigned engineer may complete this review.")
        if app.status not in (
            BusinessApplication.Status.ENGINEER_REVIEW,
            BusinessApplication.Status.FIELD_VERIFICATION,
        ):
            raise ValidationError({"status": "This application is not awaiting engineer review."})
        remarks = request.data.get("remarks", "Engineer review completed.")
        _status_change(
            app,
            BusinessApplication.Status.UNDER_REVIEW,
            request.user,
            remarks,
            request.META.get("REMOTE_ADDR"),
        )
        return success(self.get_serializer(app).data, "Engineer review completed.")

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsOfficerOrAdmin],
    )
    def review(self, request, pk=None):
        app = self.get_object()
        remarks = request.data.get("remarks", "Application placed under review.")
        _status_change(app, "UNDER_REVIEW", request.user, remarks, request.META.get("REMOTE_ADDR"))
        return success(
            self.get_serializer(app).data,
            "Application placed under review.",
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsOfficerOrAdmin],
    )
    def clarification(self, request, pk=None):
        app = self.get_object()
        message = request.data.get("message", "")
        if not message:
            raise ValidationError({"message": "This field is required."})
        _status_change(
            app,
            "CLARIFICATION_REQUESTED",
            request.user,
            f"Clarification requested: {message}",
            request.META.get("REMOTE_ADDR"),
        )
        return success(
            self.get_serializer(app).data,
            "Clarification requested.",
        )

    @action(
        detail=True,
        methods=["patch"],
        url_path="status",
        permission_classes=[IsOfficerOrAdmin],
    )
    def update_status(self, request, pk=None):
        app = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            raise ValidationError({"status": "This field is required."})
        if new_status not in BusinessApplication.Status.values:
            raise ValidationError({"status": "Invalid application status."})
        if (
            new_status == BusinessApplication.Status.FIELD_VERIFICATION
            and not app.service.field_verification_required
        ):
            raise ValidationError({"status": "Field verification is not configured for this service."})
        remarks = request.data.get("remarks", "")
        _status_change(app, new_status, request.user, remarks, request.META.get("REMOTE_ADDR"))
        return success(
            self.get_serializer(app).data,
            "Application status updated.",
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsOfficerOrAdmin],
    )
    def approve(self, request, pk=None):
        app = self.get_object()
        if app.status == "SUBMITTED":
            _status_change(
                app,
                "UNDER_REVIEW",
                request.user,
                "Officer review opened before approval.",
                request.META.get("REMOTE_ADDR"),
            )
        remarks = request.data.get("remarks", "Application approved.")
        _status_change(app, "APPROVED", request.user, remarks, request.META.get("REMOTE_ADDR"))
        return success(
            self.get_serializer(app).data,
            "Application approved.",
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsOfficerOrAdmin],
    )
    def reject(self, request, pk=None):
        app = self.get_object()
        reason = request.data.get("reason", "")
        if not reason:
            raise ValidationError({"reason": "This field is required when rejecting."})
        if app.status == "SUBMITTED":
            _status_change(
                app,
                "UNDER_REVIEW",
                request.user,
                "Officer review opened before rejection.",
                request.META.get("REMOTE_ADDR"),
            )
        app.rejection_reason = reason
        app.save(update_fields=["rejection_reason", "updated_at"])
        _status_change(app, "REJECTED", request.user, f"Rejected: {reason}", request.META.get("REMOTE_ADDR"))
        return success(
            self.get_serializer(app).data,
            "Application rejected.",
        )
