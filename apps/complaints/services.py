from rest_framework import status as http_status
from rest_framework.exceptions import APIException
from django.db import transaction
from .models import Complaint, ComplaintStatusHistory


TRANSITIONS = {
    "SUBMITTED": {"AI_PROCESSING", "CLASSIFIED", "REJECTED"},
    "AI_PROCESSING": {"CLASSIFIED", "REJECTED"},
    "CLASSIFIED": {"ASSIGNED", "REJECTED"},
    "ASSIGNED": {"IN_PROGRESS", "ON_HOLD", "REOPENED", "REJECTED"},
    "IN_PROGRESS": {"ON_HOLD", "RESOLUTION_SUBMITTED", "REOPENED", "REJECTED"},
    "ON_HOLD": {"IN_PROGRESS", "REOPENED", "REJECTED"},
    "RESOLUTION_SUBMITTED": {"VERIFICATION_PENDING", "REJECTED"},
    "VERIFICATION_PENDING": {"RESOLVED", "REOPENED", "IN_PROGRESS", "ON_HOLD"},
    "RESOLVED": {"CLOSED", "REOPENED"},
    "REOPENED": {"ASSIGNED", "IN_PROGRESS", "ON_HOLD"},
    "REJECTED": set(),
    "CLOSED": set(),
}


class InvalidStatusTransition(APIException):
    status_code = http_status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Invalid status transition."
    default_code = "BUSINESS_ERROR"


def ensure_initial_history(complaint):
    if not complaint.history.exists():
        ComplaintStatusHistory.objects.create(
            complaint=complaint,
            old_status="",
            new_status=complaint.status,
            changed_by=None,
            remarks="Complaint submitted.",
        )


@transaction.atomic
def transition(complaint, new_status, user, remarks="", ip_address=None):
    current = Complaint.objects.select_for_update().get(pk=complaint.pk)
    if new_status not in TRANSITIONS.get(current.status, set()):
        raise InvalidStatusTransition(
            f"Transition from {current.status} to {new_status} is not allowed."
        )
    old = current.status
    current.status = new_status
    current.save(update_fields=["status", "updated_at"])
    complaint.status = current.status
    complaint.updated_at = current.updated_at
    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        old_status=old,
        new_status=new_status,
        changed_by=user,
        remarks=remarks,
    )
    from apps.notifications.services import create_notification
    from apps.audit.services import record_audit

    create_notification(
        recipient=complaint.citizen,
        title="Complaint status updated",
        message=f"Your complaint status changed to {new_status.replace('_', ' ').lower()}.",
        notification_type="complaint",
        related_object_type="complaint",
        related_object_id=complaint.pk,
    )
    record_audit(
        actor=user,
        action="STATUS_CHANGED",
        entity_type="complaint",
        entity_id=complaint.pk,
        old_value={"status": old},
        new_value={"status": new_status, "remarks": remarks},
        ip_address=ip_address,
    )
    return complaint
