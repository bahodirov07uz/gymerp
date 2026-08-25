from django.contrib import admin

from .models import LedgerTransaction, Payment


@admin.register(LedgerTransaction)
class LedgerTransactionAdmin(admin.ModelAdmin):
    list_display = ("member", "transaction_type", "direction", "amount", "created_at", "created_by")
    list_filter = ("transaction_type", "direction")
    search_fields = ("member__first_name", "member__last_name", "member__member_code")
    readonly_fields = [f.name for f in LedgerTransaction._meta.fields]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("member", "amount", "payment_method", "balance_before", "balance_after", "created_at")
    list_filter = ("payment_method",)
    search_fields = ("member__first_name", "member__last_name", "member__member_code")
    readonly_fields = [f.name for f in Payment._meta.fields]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
