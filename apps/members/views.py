from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from apps.audit.services import log_action
from apps.billing.services import calculate_member_balance
from apps.memberships.services import get_active_membership

from .forms import MemberForm
from .models import Member


class MemberListView(LoginRequiredMixin, ListView):
    """Fast member search by code / phone / first / last name."""

    model = Member
    template_name = "members/list.html"
    context_object_name = "members"
    paginate_by = 25

    def get_queryset(self):
        qs = Member.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(member_code__icontains=q)
                | Q(phone__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )
        return qs.order_by("first_name", "last_name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["query"] = self.request.GET.get("q", "")
        return ctx

    def render_to_response(self, context, **kwargs):
        # HTMX partial for the fast reception search box.
        if self.request.headers.get("HX-Request"):
            return render(self.request, "members/_search_results.html", context)
        return super().render_to_response(context, **kwargs)


class MemberCreateView(LoginRequiredMixin, CreateView):
    model = Member
    form_class = MemberForm
    template_name = "members/form.html"

    def form_valid(self, form):
        form.instance.member_code = Member.generate_member_code()
        response = super().form_valid(form)
        log_action(user=self.request.user, action="member_created", obj=self.object)
        messages.success(self.request, f"{self.object.full_name} qo'shildi.")
        return response

    def get_success_url(self):
        return reverse("members:profile", args=[self.object.pk])


from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.views import View

from apps.accounts.permissions import ManagerRequiredMixin
from apps.billing.models import TransactionType
from apps.billing.services import create_payment, post_charge
from apps.memberships.models import MembershipPlan, PlanType
from apps.memberships.services import create_daily_membership, create_membership


def get_member_profile_context(member):
    """Unified context generator for member profile and its HTMX partials."""
    return {
        "member": member,
        "active_membership": get_active_membership(member),
        "memberships": member.memberships.select_related("plan").order_by("-start_date")[:20],
        "attendances": member.attendances.order_by("-date")[:20],
        "product_sales": member.product_sales.prefetch_related("items__product").order_by("-created_at")[:20],
        "payments": member.payments.order_by("-created_at")[:20],
        "ledger": member.ledger_entries.select_related("created_by").order_by("-created_at")[:50],
        "balance": calculate_member_balance(member),
        "plans": MembershipPlan.objects.filter(is_active=True).order_by("name"),
    }


class MemberProfileView(LoginRequiredMixin, DetailView):
    """Full financial + activity profile: memberships, attendance,
    purchases, payments, outstanding balance, and complete ledger."""

    model = Member
    template_name = "members/profile.html"
    context_object_name = "member"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(get_member_profile_context(self.object))
        return ctx

    def render_to_response(self, context, **kwargs):
        # From reception search: render the fast action card instead of
        # the full profile/ledger page.
        if self.request.headers.get("HX-Request") or self.request.GET.get("partial"):
            from apps.attendance.views import _member_card_context
            from apps.products.models import Product

            card_ctx = _member_card_context(self.object)
            card_ctx["products"] = Product.objects.filter(is_active=True).order_by("name")
            return render(self.request, "members/_member_card.html", card_ctx)
        return super().render_to_response(context, **kwargs)


class AddMembershipFromProfileView(LoginRequiredMixin, View):
    """Creates a monthly or daily membership directly from the profile page."""

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        plan_id = request.POST.get("plan_id")
        start_date_raw = request.POST.get("start_date", "").strip()
        error = None
        success = None

        if not plan_id:
            error = "Iltimos, a'zolik rejasini tanlang."
        else:
            plan = get_object_or_404(MembershipPlan, pk=plan_id, is_active=True)
            if start_date_raw:
                try:
                    start_date = timezone.datetime.strptime(start_date_raw, "%Y-%m-%d").date()
                except ValueError:
                    start_date = timezone.localdate()
            else:
                start_date = timezone.localdate()

            try:
                if plan.plan_type == PlanType.DAILY:
                    create_daily_membership(member=member, plan=plan, day=start_date, created_by=request.user)
                else:
                    create_membership(member=member, plan=plan, start_date=start_date, created_by=request.user)
                success = f"{plan.name} muvaffaqiyatli qo'shildi."
            except Exception as exc:
                error = str(exc)

        ctx = get_member_profile_context(member)
        ctx["membership_error"] = error
        ctx["membership_success"] = success

        if request.headers.get("HX-Request"):
            return render(request, "members/_profile_summary.html", ctx)
        return redirect("members:profile", pk=member.pk)


class AddPaymentFromProfileView(LoginRequiredMixin, View):
    """Records a payment directly from the profile page."""

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        amount_raw = request.POST.get("amount", "").strip()
        payment_method = request.POST.get("payment_method", "CASH").strip()
        note = request.POST.get("note", "").strip()
        error = None
        success = None

        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                raise ValueError("Summa musbat bo'lishi kerak.")
        except (InvalidOperation, ValueError, TypeError):
            error = "To'g'ri to'lov summasini kiriting (masalan: 100000)."

        if not error:
            try:
                create_payment(
                    member=member,
                    amount=amount,
                    payment_method=payment_method,
                    note=note or "Profil orqali to'lov",
                    created_by=request.user,
                )
                success = f"{amount:,.0f} UZS to'lov qabul qilindi."
            except Exception as exc:
                error = str(exc)

        ctx = get_member_profile_context(member)
        ctx["payment_error"] = error
        ctx["payment_success"] = success

        if request.headers.get("HX-Request"):
            return render(request, "members/_profile_summary.html", ctx)
        return redirect("members:profile", pk=member.pk)


class AddManualChargeFromProfileView(ManagerRequiredMixin, View):
    """Records a manual debt/charge directly from the profile page.
    Strictly restricted to OWNER/MANAGER roles.
    """

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        amount_raw = request.POST.get("amount", "").strip()
        description = request.POST.get("description", "").strip()
        error = None
        success = None

        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                raise ValueError("Summa musbat bo'lishi kerak.")
        except (InvalidOperation, ValueError, TypeError):
            error = "To'g'ri qarz summasini kiriting (masalan: 50000)."

        if not error:
            try:
                post_charge(
                    member=member,
                    transaction_type=TransactionType.MANUAL_CHARGE,
                    amount=amount,
                    description=description or "Qo'lda qo'shilgan qarz",
                    created_by=request.user,
                )
                success = f"{amount:,.0f} UZS qarz yozildi."
            except Exception as exc:
                error = str(exc)

        ctx = get_member_profile_context(member)
        ctx["charge_error"] = error
        ctx["charge_success"] = success

        if request.headers.get("HX-Request"):
            return render(request, "members/_profile_summary.html", ctx)
        return redirect("members:profile", pk=member.pk)


@login_required
def reception_home(request):
    """Reception landing page: search box + quick actions."""
    return render(request, "members/reception.html", {})
