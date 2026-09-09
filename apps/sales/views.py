from decimal import Decimal, InvalidOperation

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.members.models import Member
from apps.products.models import Product

from .services import create_product_sale


class AddProductSaleView(LoginRequiredMixin, View):
    """HTMX endpoint: add one or more products to the member's tab
    from the reception screen in a single atomic transaction."""

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        error = None

        # Gather products and quantities.
        # Supports both:
        # 1) `selected_products` list with per-product `quantity_<id>` fields (multi-select form)
        # 2) legacy / fallback single `product_id` + `quantity`
        selected_ids = request.POST.getlist("selected_products") or request.POST.getlist("product_id")
        
        items = []
        if not selected_ids:
            error = "Iltimos, kamida bitta mahsulotni tanlang."
        else:
            for pid in selected_ids:
                try:
                    product = Product.objects.get(pk=pid, is_active=True)
                except Product.DoesNotExist:
                    continue

                raw_qty = request.POST.get(f"quantity_{pid}") or request.POST.get("quantity", "1")
                try:
                    qty = Decimal(str(raw_qty).strip())
                    if qty <= 0:
                        qty = Decimal("1")
                except (InvalidOperation, ValueError, TypeError):
                    qty = Decimal("1")

                items.append({"product": product, "quantity": qty})

        if items and not error:
            try:
                create_product_sale(
                    member=member,
                    items=items,
                    created_by=request.user,
                )
            except ValueError as exc:
                error = str(exc)
            except Exception as exc:
                error = str(exc)

        from apps.attendance.views import _member_card_context
        ctx = _member_card_context(member)
        ctx["products"] = Product.objects.filter(is_active=True).order_by("name")
        ctx["sale_error"] = error
        return render(request, "members/_member_card.html", ctx)
