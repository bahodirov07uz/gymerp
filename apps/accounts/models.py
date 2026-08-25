from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    OWNER = "OWNER", "Owner"
    MANAGER = "MANAGER", "Manager"
    RECEPTIONIST = "RECEPTIONIST", "Receptionist"


class User(AbstractUser):
    """Custom user with a gym-specific role used for permission checks."""

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RECEPTIONIST)
    phone = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_owner(self):
        return self.role == Role.OWNER or self.is_superuser

    @property
    def is_manager(self):
        return self.role in (Role.OWNER, Role.MANAGER) or self.is_superuser

    @property
    def is_receptionist(self):
        return self.role == Role.RECEPTIONIST

    def can_manage_finance(self):
        """Only owners/managers may reverse or adjust financial records."""
        return self.is_manager

    def can_modify_settings(self):
        return self.is_owner
