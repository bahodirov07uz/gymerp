"""Membership service layer.

Handles both monthly and daily membership creation, always storing the
price actually charged (``price_at_purchase``) so later catalogue price
changes never rewrite history, and always posting a matching ledger
charge in the same transaction.
"""
import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_action
from apps.billing.models import TransactionType
from apps.billing.services import post_charge

from .models import Membership, MembershipStatus, PlanType


class DuplicateMembershipError(Exception):
    """Raised when a member already has an active monthly membership and a
    new one is requested before the existing one expires.

    The `existing_end_date` attribute carries the expiry date for use in
    UI messages such as 'A new membership can be added from {end_date}'."""

    def __init__(self, existing_end_date):
        self.existing_end_date = existing_end_date
        super().__init__(
            f"A'zoda allaqachon faol oylik a'zolik bor (tugaydi: {existing_end_date}). "
            f"Yangi a'zolik {existing_end_date + datetime.timedelta(days=1)} kundan keyin qo'shilishi mumkin."
        )


@transaction.atomic
def create_membership(*, member, plan, start_date=None, created_by=None):
    """Create a MONTHLY (or generic multi-day) membership and its charge.

    Raises ``DuplicateMembershipError`` if the member already has an
    active MONTHLY membership that has not yet expired.
    """
    start_date = start_date or timezone.localdate()
    end_date = start_date + datetime.timedelta(days=plan.duration_days - 1)

    # Block duplicate active MONTHLY memberships at service layer
    if plan.plan_type == PlanType.MONTHLY:
        existing = Membership.objects.filter(
            member=member,
            plan__plan_type=PlanType.MONTHLY,
            status=MembershipStatus.ACTIVE,
            end_date__gte=start_date,
        ).order_by("-end_date").first()
        if existing:
            raise DuplicateMembershipError(existing.end_date)

    membership = Membership.objects.create(
        member=member,
        plan=plan,
        start_date=start_date,
        end_date=end_date,
        price_at_purchase=plan.price,
        status=MembershipStatus.ACTIVE,
        created_by=created_by,
    )

    charge_type = (
        TransactionType.DAILY_CHARGE if plan.plan_type == PlanType.DAILY
        else TransactionType.MEMBERSHIP_CHARGE
    )
    post_charge(
        member=member,
        transaction_type=charge_type,
        amount=plan.price,
        description=f"{plan.name} ({start_date} - {end_date})",
        reference=membership,
        created_by=created_by,
    )

    log_action(user=created_by, action="membership_created", obj=membership, metadata={
        "member_id": member.pk, "plan": plan.name, "price": str(plan.price),
    })
    return membership


@transaction.atomic
def create_daily_membership(*, member, plan, day=None, created_by=None):
    """Create (or return the existing) daily membership/charge for a
    specific day. Never creates a duplicate charge for the same day."""
    day = day or timezone.localdate()

    existing = Membership.objects.filter(
        member=member, plan=plan, start_date=day, end_date=day,
        status=MembershipStatus.ACTIVE,
    ).first()
    if existing:
        return existing, False

    membership = Membership.objects.create(
        member=member,
        plan=plan,
        start_date=day,
        end_date=day,
        price_at_purchase=plan.price,
        status=MembershipStatus.ACTIVE,
        created_by=created_by,
    )
    post_charge(
        member=member,
        transaction_type=TransactionType.DAILY_CHARGE,
        amount=plan.price,
        description=f"{plan.name} ({day})",
        reference=membership,
        created_by=created_by,
    )
    log_action(user=created_by, action="membership_created", obj=membership, metadata={
        "member_id": member.pk, "plan": plan.name, "price": str(plan.price), "daily": True,
    })
    return membership, True


def get_active_membership(member, on_date=None):
    on_date = on_date or timezone.localdate()
    return (
        Membership.objects.filter(
            member=member, status=MembershipStatus.ACTIVE,
            start_date__lte=on_date, end_date__gte=on_date,
        )
        .order_by("-end_date")
        .first()
    )


def expire_outdated_memberships(as_of=None):
    """Batch job (run daily via Celery beat / management command) that
    flips ACTIVE memberships whose end_date has passed to EXPIRED."""
    as_of = as_of or timezone.localdate()
    return Membership.objects.filter(
        status=MembershipStatus.ACTIVE, end_date__lt=as_of,
    ).update(status=MembershipStatus.EXPIRED)


def memberships_expiring_within(days: int, as_of=None):
    as_of = as_of or timezone.localdate()
    horizon = as_of + datetime.timedelta(days=days)
    return Membership.objects.filter(
        status=MembershipStatus.ACTIVE, end_date__gte=as_of, end_date__lte=horizon,
    ).select_related("member", "plan")
