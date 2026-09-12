from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Immutable trail of important actions across the system."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Foydalanuvchi", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="audit_logs",
    )
    action = models.CharField("Amal", max_length=64)
    object_type = models.CharField("Obyekt turi", max_length=64)
    object_id = models.CharField("Obyekt ID", max_length=64, blank=True)
    metadata = models.JSONField("Qo'shimcha ma'lumot", default=dict, blank=True)
    timestamp = models.DateTimeField("Vaqt", auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Audit yozuvi"
        verbose_name_plural = "Audit yozuvlari"
        indexes = [
            models.Index(fields=["object_type", "object_id"]),
            models.Index(fields=["-timestamp"]),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.action} {self.object_type}#{self.object_id}"
