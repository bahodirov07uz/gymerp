from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "sale_price", "stock_quantity", "low_stock_threshold", "is_active")
    search_fields = ("name", "sku")
    list_filter = ("is_active",)
