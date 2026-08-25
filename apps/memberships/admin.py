from django.contrib import admin

from .models import Membership, MembershipPlan


@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "plan_type", "price", "duration_days", "is_active")
    list_filter = ("plan_type", "is_active")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("member", "plan", "start_date", "end_date", "price_at_purchase", "status")
    list_filter = ("status", "plan__plan_type")
    search_fields = ("member__first_name", "member__last_name", "member__member_code")
    autocomplete_fields = ["member"]
