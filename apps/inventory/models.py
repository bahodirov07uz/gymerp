from django.conf import settings
from django.db import models


class AdjustmentReason(models.TextChoices):
    RESTOCK = "RESTOCK", "Yangi yetkazib berish"
    SALE = "SALE", "Sotuv"
    CORRECTION = "CORRECTION", "Tuzatish"
    DAMAGE = "DAMAGE", "Yaroqsiz/Zarar"
    OTHER = "OTHER", "Boshqa"


class StockMovement(models.Model):
    """Every single stock change is recorded here so inventory levels
    are always auditable and explainable after the fact."""

    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="stock_movements")
    reason = models.CharField(max_length=20, choices=AdjustmentReason.choices)
    quantity_delta = models.DecimalField(max_digits=12, decimal_places=3, help_text="Positive=in, negative=out")
    quantity_after = models.DecimalField(max_digits=12, decimal_places=3)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "created_at"])]

    def __str__(self):
        return f"{self.product} {self.quantity_delta:+} ({self.reason})"
