from django.contrib import admin

from .models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("member_code", "full_name_display", "phone", "is_active", "created_at")
    search_fields = ("member_code", "first_name", "last_name", "phone")
    list_filter = ("is_active", "gender")

    @admin.display(description="F.I.Sh.", ordering="first_name")
    def full_name_display(self, obj):
        return obj.full_name
