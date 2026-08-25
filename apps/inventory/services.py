"""Inventory service layer -- the only place allowed to change
``Product.stock_quantity``. Never silently modify stock elsewhere."""
from decimal import Decimal

from django.db import transaction

from apps.audit.services import log_action

from .models import AdjustmentReason, StockMovement


@transaction.atomic
def adjust_inventory(*, product, quantity_delta: Decimal, reason: str, note="", created_by=None,
                      allow_negative=False):
    """Apply a signed quantity change to a product's stock and record
    an auditable StockMovement row in the same transaction."""
    # lock the product row to avoid race conditions on concurrent sales
    from apps.products.models import Product
    locked_product = Product.objects.select_for_update().get(pk=product.pk)

    new_quantity = locked_product.stock_quantity + quantity_delta
    if new_quantity < 0 and not allow_negative:
        raise ValueError(
            f"Yetarli mahsulot yo'q: {locked_product.name} qoldig'i {locked_product.stock_quantity}, "
            f"so'ralgan {abs(quantity_delta)}."
        )

    locked_product.stock_quantity = new_quantity
    locked_product.save(update_fields=["stock_quantity", "updated_at"])

    movement = StockMovement.objects.create(
        product=locked_product,
        reason=reason,
        quantity_delta=quantity_delta,
        quantity_after=new_quantity,
        note=note,
        created_by=created_by,
    )
    log_action(user=created_by, action="inventory_adjusted", obj=movement, metadata={
        "product_id": locked_product.pk, "delta": str(quantity_delta), "after": str(new_quantity),
    })
    return movement


def restock(*, product, quantity: Decimal, note="", created_by=None):
    if quantity <= 0:
        raise ValueError("Restock quantity must be positive.")
    return adjust_inventory(
        product=product, quantity_delta=quantity, reason=AdjustmentReason.RESTOCK,
        note=note, created_by=created_by,
    )
