"""Product sale service layer.

A sale must, atomically:
    1. reduce inventory (never silently)
    2. create a ledger charge (member owes the total)
    3. be traceable to the staff member who created it
If stock is insufficient, the whole sale is rejected.
"""
from decimal import Decimal

from django.db import transaction

from apps.audit.services import log_action
from apps.billing.models import TransactionType
from apps.billing.services import post_charge
from apps.inventory.models import AdjustmentReason
from apps.inventory.services import adjust_inventory

from .models import ProductSale, ProductSaleItem


@transaction.atomic
def create_product_sale(*, member, items, created_by=None):
    """``items`` is a list of dicts: [{"product": Product, "quantity": Decimal}, ...]

    Raises ValueError (rolling back everything) if any line has
    insufficient stock, so partial sales never occur.
    """
    if not items:
        raise ValueError("Sale must contain at least one item.")

    sale = ProductSale.objects.create(member=member, created_by=created_by, total_amount=Decimal("0"))
    total = Decimal("0")

    for line in items:
        product = line["product"]
        quantity = Decimal(line["quantity"])
        if quantity <= 0:
            raise ValueError(f"Invalid quantity for {product.name}.")

        unit_price = line.get("unit_price", product.sale_price)
        line_total = (unit_price * quantity).quantize(Decimal("0.01"))

        # reduce stock -- raises ValueError and rolls back the whole
        # sale if there isn't enough on hand.
        adjust_inventory(
            product=product,
            quantity_delta=-quantity,
            reason=AdjustmentReason.SALE,
            note=f"Sotuv #{sale.pk}",
            created_by=created_by,
        )

        ProductSaleItem.objects.create(
            sale=sale, product=product, quantity=quantity,
            unit_price=unit_price, line_total=line_total,
        )
        total += line_total

    sale.total_amount = total
    sale.save(update_fields=["total_amount"])

    description = ", ".join(f"{i['product'].name}" for i in items)
    post_charge(
        member=member,
        transaction_type=TransactionType.PRODUCT_CHARGE,
        amount=total,
        description=f"Mahsulotlar: {description}",
        reference=sale,
        created_by=created_by,
    )

    log_action(user=created_by, action="product_sold", obj=sale, metadata={
        "member_id": member.pk, "total": str(total), "item_count": len(items),
    })
    return sale
