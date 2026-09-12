from django.conf import settings
from django.db import models


class ProductSale(models.Model):
    """A single checkout event; may contain multiple ProductSaleItem rows."""

    member = models.ForeignKey("members.Member", verbose_name="A'zo", on_delete=models.PROTECT, related_name="product_sales")
    total_amount = models.DecimalField("Jami summa", max_digits=14, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Yaratgan", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Mahsulot sotuvi"
        verbose_name_plural = "Mahsulot sotuvlari"
        indexes = [models.Index(fields=["member", "created_at"])]

    def __str__(self):
        return f"Sotuv #{self.pk} - {self.member} - {self.total_amount}"


class ProductSaleItem(models.Model):
    sale = models.ForeignKey(ProductSale, verbose_name="Sotuv", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", verbose_name="Mahsulot", on_delete=models.PROTECT, related_name="sale_items")
    quantity = models.DecimalField("Miqdor", max_digits=12, decimal_places=3)
    unit_price = models.DecimalField("Birlik narxi", max_digits=12, decimal_places=2)
    line_total = models.DecimalField("Qator summasi", max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = "Sotuv qatori"
        verbose_name_plural = "Sotuv qatorlari"

    def __str__(self):
        return f"{self.product} x{self.quantity} = {self.line_total}"
