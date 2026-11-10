from .models import Notification


def create_notification(
    *, recipient, title, message, notification_type="system",
    related_object_type="", related_object_id=None,
):
    related_id = str(related_object_id) if related_object_id is not None else ""
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        type=notification_type,
        related_id=related_id,
        related_object_type=related_object_type,
        related_object_id=related_id,
    )