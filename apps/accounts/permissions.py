"""Reusable permission mixins/decorators enforcing the role matrix.

RECEPTIONIST must NOT be able to:
    - delete financial transactions
    - modify historical payments
    - change product cost
    - modify system settings
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """View requires OWNER or MANAGER role."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_manager

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("Bu amal uchun ruxsatingiz yo'q.")


class OwnerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """View requires OWNER role."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_owner

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("Faqat egasi uchun.")


def require_manager(user):
    if not (user.is_authenticated and user.is_manager):
        raise PermissionDenied("Bu amal uchun ruxsatingiz yo'q.")
