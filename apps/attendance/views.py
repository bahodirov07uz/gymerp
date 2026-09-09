from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View

from apps.members.models import Member
from apps.memberships.models import MembershipPlan, PlanType
from apps.memberships.services import create_daily_membership, get_active_membership
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

    today = timezone.localdate()
    in_gym = Attendance.objects.filter(
        date=today, check_out__isnull=True
    ).select_related("member", "membership__plan").order_by("-check_in")

    in_gym_html = render_to_string("members/_in_gym_list.html", {"in_gym_list": in_gym}, request=request)
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
        today = timezone.localdate()
        attendance = member.attendances.filter(date=today, check_out__isnull=True).first()
        if attendance:
            check_out_member(attendance=attendance, created_by=request.user)
        return _render_with_in_gym_oob(request, member)


class InGymListView(LoginRequiredMixin, View):
    """HTMX endpoint returning the list of members currently inside the gym."""

    def get(self, request):
        today = timezone.localdate()
        in_gym = Attendance.objects.filter(
            date=today, check_out__isnull=True
        ).select_related("member", "membership__plan").order_by("-check_in")
        return render(request, "members/_in_gym_list.html", {"in_gym_list": in_gym})


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


def _member_card_context(member):
    today = timezone.localdate()
    today_sessions = list(member.attendances.filter(date=today).order_by("check_in"))
    open_session = next((a for a in today_sessions if a.check_out is None), None)

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
