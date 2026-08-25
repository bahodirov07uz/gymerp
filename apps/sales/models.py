from django.conf import settings
from django.db import models


class ProductSale(models.Model):
    """A single checkout event; may contain multiple ProductSaleItem rows."""

    member = models.ForeignKey("members.Member", on_delete=models.PROTECT, related_name="product_sales")
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["member", "created_at"])]

    def __str__(self):
        return f"Sotuv #{self.pk} - {self.member} - {self.total_amount}"


class ProductSaleItem(models.Model):
    sale = models.ForeignKey(ProductSale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="sale_items")
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)

    def __str__(self):
        return f"{self.product} x{self.quantity} = {self.line_total}"
