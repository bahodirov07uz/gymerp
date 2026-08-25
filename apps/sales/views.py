from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.members.models import Member
from apps.products.models import Product

from .services import create_product_sale


class AddProductSaleView(LoginRequiredMixin, View):
    """HTMX endpoint: add a single product line to the member's tab
    from the reception screen."""

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        product_id = request.POST.get("product_id")
        quantity = request.POST.get("quantity", "1")
        error = None

        product = get_object_or_404(Product, pk=product_id)
        try:
            create_product_sale(
                member=member,
                items=[{"product": product, "quantity": quantity}],
                created_by=request.user,
            )
        except ValueError as exc:
            error = str(exc)

        from apps.attendance.views import _member_card_context
        ctx = _member_card_context(member)
        ctx["products"] = Product.objects.filter(is_active=True).order_by("name")
        ctx["sale_error"] = error
        return render(request, "members/_member_card.html", ctx)
