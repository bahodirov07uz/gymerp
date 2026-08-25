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


class MemberProfileView(LoginRequiredMixin, DetailView):
    """Full financial + activity profile: memberships, attendance,
    purchases, payments, outstanding balance, and complete ledger."""

    model = Member
    template_name = "members/profile.html"
    context_object_name = "member"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        member = self.object
        ctx["active_membership"] = get_active_membership(member)
        ctx["memberships"] = member.memberships.select_related("plan").order_by("-start_date")[:20]
        ctx["attendances"] = member.attendances.order_by("-date")[:20]
        ctx["product_sales"] = member.product_sales.prefetch_related("items__product").order_by("-created_at")[:20]
        ctx["payments"] = member.payments.order_by("-created_at")[:20]
        ctx["ledger"] = member.ledger_entries.select_related("created_by").order_by("-created_at")[:50]
        ctx["balance"] = calculate_member_balance(member)
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


@login_required
def reception_home(request):
    """Reception landing page: search box + quick actions."""
    return render(request, "members/reception.html", {})
