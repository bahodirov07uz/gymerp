"""Stashes the current request's user in thread-local storage so that
model ``save()``/service functions that don't receive an explicit
``created_by`` can still be attributed for audit purposes if needed.
Primarily used for login auditing.
"""
import threading

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .services import log_action

_thread_locals = threading.local()


def get_current_user():
    return getattr(_thread_locals, "user", None)


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, "user", None)
        response = self.get_response(request)
        return response


@receiver(user_logged_in)
def audit_login(sender, request, user, **kwargs):
    log_action(user=user, action="user_login", obj=user)
