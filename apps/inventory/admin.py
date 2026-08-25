from django.contrib import admin

from .models import StockMovement


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "reason", "quantity_delta", "quantity_after", "created_at", "created_by")
    list_filter = ("reason",)
    search_fields = ("product__name", "product__sku")
    readonly_fields = [f.name for f in StockMovement._meta.fields]

    def has_delete_permission(self, request, obj=None):
        return False
