from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from apps.accounts.permissions import ManagerRequiredMixin
from apps.products.models import Product

from .services import restock


class InventoryListView(ManagerRequiredMixin, ListView):
    model = Product
    template_name = "inventory/list.html"
    context_object_name = "products"

    def get_queryset(self):
        return Product.objects.all().order_by("name")


class RestockView(ManagerRequiredMixin, View):
    """Simple POST-only restock action, redirects back to inventory list."""

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        raw_qty = request.POST.get("quantity", "").strip()
        note = request.POST.get("note", "")
        try:
            quantity = Decimal(raw_qty)
            restock(product=product, quantity=quantity, note=note, created_by=request.user)
            messages.success(request, f"{product.name} qoldig'i to'ldirildi.")
        except (InvalidOperation, ValueError) as exc:
            msg = "Noto'g'ri miqdor kiritildi." if isinstance(exc, InvalidOperation) else str(exc)
            messages.error(request, msg)
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect(reverse("inventory:list"))
