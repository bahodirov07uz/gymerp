from django.contrib import admin

from .models import ProductSale, ProductSaleItem


class ProductSaleItemInline(admin.TabularInline):
    model = ProductSaleItem
    extra = 0
    readonly_fields = ("product", "quantity", "unit_price", "line_total")
    can_delete = False


@admin.register(ProductSale)
class ProductSaleAdmin(admin.ModelAdmin):
    list_display = ("id", "member", "total_amount", "created_at", "created_by")
    search_fields = ("member__first_name", "member__last_name", "member__member_code")
    inlines = [ProductSaleItemInline]
    readonly_fields = ("member", "total_amount", "created_by", "created_at")

    def has_delete_permission(self, request, obj=None):
        return False
