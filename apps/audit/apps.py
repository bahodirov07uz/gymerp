from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    label = "audit"
    verbose_name = "Audit jurnali"

    def ready(self):
        from . import middleware  # noqa: F401  (registers user_logged_in signal)
