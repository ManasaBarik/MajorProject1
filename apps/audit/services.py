from .models import AuditLog


def record_audit(
    *, actor, action, entity_type, entity_id, old_value=None,
    new_value=None, ip_address=None,
):
    return AuditLog.objects.create(
        user=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity=entity_type,
        entity_id=str(entity_id),
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        metadata={
            "old_value": old_value,
            "new_value": new_value,
            "ip_address": ip_address,
        },
    )