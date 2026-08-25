from decimal import Decimal, InvalidOperation

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import ListView

from apps.accounts.permissions import ManagerRequiredMixin
from apps.members.models import Member

from .models import PaymentMethod, LedgerTransaction
from .services import create_payment, debtors_queryset, reverse_transaction


class ReceivePaymentView(LoginRequiredMixin, View):
    """HTMX endpoint used from the reception member card."""

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        raw_amount = request.POST.get("amount", "").strip()
        method = request.POST.get("payment_method", PaymentMethod.CASH)
        error = None
        receipt = None
        try:
            amount = Decimal(raw_amount)
            receipt = create_payment(
                member=member, amount=amount, payment_method=method, created_by=request.user,
            )
        except (InvalidOperation, ValueError) as exc:
            error = "Noto'g'ri summa kiritildi." if isinstance(exc, InvalidOperation) else str(exc)
        except Exception as exc:
            error = str(exc)

        from apps.attendance.views import _member_card_context
        from apps.products.models import Product
        ctx = _member_card_context(member)
        ctx["payment_error"] = error
        ctx["last_receipt"] = receipt
        ctx["products"] = Product.objects.filter(is_active=True).order_by("name")
        return render(request, "members/_member_card.html", ctx)


class DebtorsListView(LoginRequiredMixin, ListView):
    """Members sorted by highest outstanding balance (N+1-free annotate query)."""

    template_name = "billing/debtors.html"
    context_object_name = "debtors"
    paginate_by = 50

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip()
        return debtors_queryset(search=q)


class ReverseLedgerEntryView(LoginRequiredMixin, View):
    """Only OWNER/MANAGER may reverse a financial entry --
    financial records are otherwise immutable."""

    def post(self, request, pk):
        from apps.accounts.permissions import require_manager
        require_manager(request.user)
        entry = get_object_or_404(LedgerTransaction, pk=pk)
        reason = request.POST.get("reason", "Manual correction")
        reverse_transaction(ledger_entry=entry, reason=reason, created_by=request.user)
        from apps.attendance.views import _member_card_context
        from apps.products.models import Product
        ctx = _member_card_context(entry.member)
        ctx["products"] = Product.objects.filter(is_active=True).order_by("name")
        return render(request, "members/_member_card.html", ctx)
