from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View

from apps.members.models import Member
from apps.memberships.models import MembershipPlan, PlanType
from apps.memberships.services import create_daily_membership, get_active_membership
from apps.billing.services import calculate_member_balance
from apps.products.models import Product

from .models import Attendance
from .services import AlreadyCheckedIn, DailyPlanRequired, check_in_member, check_out_member


class CheckInView(LoginRequiredMixin, View):
    """HTMX endpoint used from the reception member card."""

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        try:
            check_in_member(member=member, created_by=request.user)
        except DailyPlanRequired:
            pass  # fall through: template shows "Daily plan required" prompt
        except AlreadyCheckedIn:
            pass
        return render(request, "members/_member_card.html", _member_card_context(member))


class CheckOutView(LoginRequiredMixin, View):
    """HTMX endpoint to check out a member currently in gym."""

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        today = timezone.localdate()
        attendance = member.attendances.filter(date=today, check_out__isnull=True).first()
        if attendance:
            check_out_member(attendance=attendance, created_by=request.user)
        return render(request, "members/_member_card.html", _member_card_context(member))


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
        if plan:
            create_daily_membership(member=member, plan=plan, created_by=request.user)
            try:
                check_in_member(member=member, created_by=request.user)
            except AlreadyCheckedIn:
                pass
        return render(request, "members/_member_card.html", _member_card_context(member))


def _member_card_context(member):
    today = timezone.localdate()
    return {
        "member": member,
        "active_membership": get_active_membership(member),
        "balance": calculate_member_balance(member),
        "today_attendance": member.attendances.filter(date=today).first(),
        "today_sales": member.product_sales.filter(created_at__date=today).prefetch_related("items__product"),
        "products": Product.objects.filter(is_active=True).order_by("name"),
    }
