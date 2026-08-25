"""Central helper for writing audit trail entries.

Every business-critical mutation (member created, membership created,
payment created, product sold, inventory adjusted, financial
adjustment, login) should call ``log_action`` so there is a durable,
human-readable trail independent of the domain tables.
"""
from .models import AuditLog


def log_action(*, user, action, obj, metadata=None):
    return AuditLog.objects.create(
        user=user if (user and getattr(user, "is_authenticated", False)) else None,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(getattr(obj, "pk", "") or ""),
        metadata=metadata or {},
    )
