from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.members.models import Member
from .models import MembershipPlan
from .services import DuplicateMembershipError, create_membership


class CreateMembershipView(LoginRequiredMixin, View):
    """Adds a new membership plan to a member."""

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        plan_id = request.POST.get("plan_id")
        start_date_str = request.POST.get("start_date")
        plan = get_object_or_404(MembershipPlan, pk=plan_id)

        start_date = None
        if start_date_str:
            import datetime
            try:
                start_date = datetime.date.fromisoformat(start_date_str)
            except ValueError:
                pass

        try:
            membership = create_membership(
                member=member,
                plan=plan,
                start_date=start_date,
                created_by=request.user,
            )
            messages.success(request, f"{plan.name} a'zoligi muvaffaqiyatli qo'shildi ({membership.start_date} - {membership.end_date}).")
        except DuplicateMembershipError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f"Xatolik: {exc}")

        if request.headers.get("HX-Request"):
            from apps.attendance.views import _member_card_context
            from apps.products.models import Product
            ctx = _member_card_context(member)
            ctx["products"] = Product.objects.filter(is_active=True).order_by("name")
            return render(request, "members/_member_card.html", ctx)

        return redirect(reverse("members:profile", args=[member.pk]))
