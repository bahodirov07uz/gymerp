from django.contrib import admin

from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("member", "date", "check_in", "check_out")
    search_fields = ("member__first_name", "member__last_name", "member__member_code")
    list_filter = ("date",)
