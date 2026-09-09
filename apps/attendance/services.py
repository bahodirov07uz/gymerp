"""Attendance service layer."""
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import log_action
from apps.memberships.services import get_active_membership

from .models import Attendance


class DailyPlanRequired(Exception):
    """Raised when a member has no active membership and no daily plan
    was supplied, so reception must prompt for one."""


class AlreadyCheckedIn(Exception):
    pass


@transaction.atomic
def check_in_member(*, member, created_by=None):
    """Check a member in. Requires an active membership (monthly or daily).

    A member may check in multiple times per day — each time they must
    have checked out of the previous session first. This is enforced by
    the DB-level partial unique constraint on (member) WHERE check_out IS NULL,
    and by the explicit open-session guard below.
    """
    today = timezone.localdate()

    # Guard: is there an OPEN (unchecked-out) session right now?
    if Attendance.objects.filter(member=member, check_out__isnull=True).exists():
        raise AlreadyCheckedIn(
            f"{member.full_name} hozir zalda — avval chiqishni belgilang."
        )

    membership = get_active_membership(member, on_date=today)
    if membership is None:
        raise DailyPlanRequired("Faol a'zolik topilmadi. Kunlik reja kerak.")

    try:
        attendance = Attendance.objects.create(
            member=member, date=today, check_in=timezone.now(),
            membership=membership, created_by=created_by,
        )
    except IntegrityError:
        # Partial constraint hit (race condition) — treat as already checked in
        raise AlreadyCheckedIn(
            f"{member.full_name} hozir zalda — avval chiqishni belgilang."
        )

    log_action(user=created_by, action="attendance_checked_in", obj=attendance, metadata={
        "member_id": member.pk,
    })
    return attendance


def check_out_member(*, attendance, created_by=None):
    attendance.check_out = timezone.now()
    attendance.save(update_fields=["check_out"])
    log_action(user=created_by, action="attendance_checked_out", obj=attendance, metadata={
        "member_id": attendance.member_id,
    })
    return attendance
