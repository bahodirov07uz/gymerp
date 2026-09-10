from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View

from decimal import Decimal
from django.db.models import Case, DecimalField, F, Sum, Value, When
from django.db.models.functions import Coalesce

from apps.members.models import Member
from apps.memberships.models import MembershipPlan, PlanType
from apps.memberships.services import create_daily_membership, get_active_membership
from apps.billing.models import Direction, LedgerTransaction
from apps.billing.services import calculate_member_balance
from apps.products.models import Product

from .models import Attendance
from .services import AlreadyCheckedIn, DailyPlanRequired, check_in_member, check_out_member


def _render_with_in_gym_oob(request, member, extra_ctx=None):
    """Renders _member_card.html AND appends _in_gym_list.html wrapped in
    <div id="in-gym-panel" hx-swap-oob="true">...</div> so that HTMX updates
    both the active member card and the reception in-gym live list in ONE response."""
    ctx = _member_card_context(member)
    if extra_ctx:
        ctx.update(extra_ctx)
    card_html = render_to_string("members/_member_card.html", ctx, request=request)

    # No date filter — any unclosed session stays visible regardless of when it was opened
    in_gym = Attendance.objects.filter(
        check_out__isnull=True
    ).select_related("member", "membership__plan").order_by("check_in")

    in_gym_html = render_to_string("members/_in_gym_list.html", {
        "in_gym_list": in_gym,
        "today": timezone.localdate(),
    }, request=request)
    oob_in_gym = f'<div id="in-gym-panel" hx-swap-oob="true">{in_gym_html}</div>'

    return HttpResponse(card_html + oob_in_gym)


class CheckInView(LoginRequiredMixin, View):
    """HTMX endpoint used from the reception member card."""

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        error = None
        try:
            check_in_member(member=member, created_by=request.user)
        except (DailyPlanRequired, AlreadyCheckedIn) as exc:
            error = str(exc)
        return _render_with_in_gym_oob(request, member, {"checkin_error": error})


class CheckOutView(LoginRequiredMixin, View):
    """HTMX endpoint to check out a member currently in gym."""

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        # No date filter — an unclosed session from a previous day can also be checked out
        attendance = member.attendances.filter(check_out__isnull=True).first()
        if attendance:
            check_out_member(attendance=attendance, created_by=request.user)
        return _render_with_in_gym_oob(request, member)


class InGymListView(LoginRequiredMixin, View):
    """HTMX endpoint returning the list of members currently inside the gym.

    Intentionally does NOT filter by date — any session without check_out
    is considered 'in gym', even if it was opened on a previous day.
    This keeps the logic consistent with _member_card_context's open_session check.
    """

    def get(self, request):
        in_gym = Attendance.objects.filter(
            check_out__isnull=True
        ).select_related("member", "membership__plan").order_by("check_in")
        return render(request, "members/_in_gym_list.html", {
            "in_gym_list": in_gym,
            "today": timezone.localdate(),
        })


class AddDailyPlanView(LoginRequiredMixin, View):
    """Creates today's daily membership charge, then attempts check-in."""

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        plan = MembershipPlan.objects.filter(plan_type=PlanType.DAILY, is_active=True).first()
        error = None
        if plan:
            create_daily_membership(member=member, plan=plan, created_by=request.user)
            try:
                check_in_member(member=member, created_by=request.user)
            except AlreadyCheckedIn as exc:
                error = str(exc)
        return _render_with_in_gym_oob(request, member, {"checkin_error": error})


class AttendanceBoardView(LoginRequiredMixin, View):
    """Full attendance board with in-gym members table and quick search."""

    def get(self, request):
        today = timezone.localdate()
        in_gym = list(
            Attendance.objects.filter(check_out__isnull=True)
            .select_related("member", "membership__plan")
            .order_by("check_in")
        )

        member_ids = [att.member_id for att in in_gym]
        balances = {}
        if member_ids:
            ledger_totals = (
                LedgerTransaction.objects.filter(member_id__in=member_ids)
                .values("member_id")
                .annotate(
                    balance=Coalesce(
                        Sum(
                            Case(
                                When(direction=Direction.DEBIT, then=F("amount")),
                                When(direction=Direction.CREDIT, then=-F("amount")),
                                output_field=DecimalField(max_digits=14, decimal_places=2),
                            )
                        ),
                        Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2)),
                    )
                )
            )
            balances = {row["member_id"]: row["balance"] for row in ledger_totals}

        for att in in_gym:
            att.member_balance = balances.get(att.member_id, Decimal("0.00"))

        return render(
            request,
            "attendance/board.html",
            {
                "in_gym_list": in_gym,
                "today": today,
            },
        )


class AttendanceRowCheckOutView(LoginRequiredMixin, View):
    """HTMX endpoint to check out a member directly from a table row."""

    def post(self, request, pk):
        attendance = get_object_or_404(Attendance, pk=pk, check_out__isnull=True)
        check_out_member(attendance=attendance, created_by=request.user)
        return HttpResponse("")


def _member_card_context(member):
    today = timezone.localdate()
    today_sessions = list(member.attendances.filter(date=today).order_by("check_in"))
    # open_session must NOT be filtered by date — keeps logic consistent with InGymListView
    open_session = member.attendances.filter(check_out__isnull=True).first()

    return {
        "member": member,
        "active_membership": get_active_membership(member),
        "balance": calculate_member_balance(member),
        "open_session": open_session,
        "today_sessions": today_sessions,
        "today_attendance": open_session or (today_sessions[-1] if today_sessions else None),
        "today_sales": member.product_sales.filter(created_at__date=today).prefetch_related("items__product"),
        "products": Product.objects.filter(is_active=True).order_by("name"),
    }
