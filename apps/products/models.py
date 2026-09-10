from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50, unique=True)
    unit = models.CharField(max_length=20, default="dona", help_text="e.g. dona, kg, litr")
    sale_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    low_stock_threshold = models.DecimalField(max_digits=12, decimal_places=3, default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.stock_quantity} {self.unit})"

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_threshold

    @property
    def stock_value(self):
        base = self.cost_price if self.cost_price is not None else self.sale_price
        return base * self.stock_quantity
