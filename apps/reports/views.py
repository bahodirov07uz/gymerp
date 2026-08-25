import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from apps.memberships.services import memberships_expiring_within

from . import services


class DailyReportView(LoginRequiredMixin, View):
    def get(self, request):
        date_str = request.GET.get("date")
        try:
            day = datetime.date.fromisoformat(date_str) if date_str else timezone.localdate()
        except ValueError:
            day = timezone.localdate()
        ctx = {
            "day": day,
            "revenue": services.revenue_for_range(day, day),
            "payments": services.payments_for_range(day, day),
            "attendance": services.attendance_for_range(day, day),
            "new_members": services.new_members_for_range(day, day),
            "best_sellers": services.best_selling_products(day, day),
        }
        return render(request, "reports/daily.html", ctx)


class MonthlyReportView(LoginRequiredMixin, View):
    def get(self, request):
        month_str = request.GET.get("month")  # YYYY-MM
        today = timezone.localdate()
        try:
            if month_str:
                year, month = (int(x) for x in month_str.split("-"))
            else:
                year, month = today.year, today.month
            start = datetime.date(year, month, 1)
        except (ValueError, TypeError):
            year, month = today.year, today.month
            start = today.replace(day=1)
        end = (datetime.date(year + (month == 12), (month % 12) + 1, 1) - datetime.timedelta(days=1))
        end = min(end, today) if (year, month) == (today.year, today.month) else end

        ctx = {
            "start": start, "end": end,
            "revenue": services.revenue_for_range(start, end),
            "payments": services.payments_for_range(start, end),
            "outstanding_debt": services.total_outstanding_debt(),
            "new_members": services.new_members_for_range(start, end),
            "active_members": services.dashboard_summary()["active_members"],
            "attendance": services.attendance_for_range(start, end),
            "best_sellers": services.best_selling_products(start, end),
        }
        return render(request, "reports/monthly.html", ctx)


class ProductReportView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.localdate()
        start = today - datetime.timedelta(days=30)
        ctx = {
            "start": start, "end": today,
            "best_sellers": services.best_selling_products(start, today, limit=50),
            "low_stock": services.low_stock_products(),
        }
        return render(request, "reports/products.html", ctx)


class ExpiringMembershipsView(LoginRequiredMixin, View):
    def get(self, request):
        ctx = {
            "today": memberships_expiring_within(0),
            "tomorrow": memberships_expiring_within(1),
            "within_3_days": memberships_expiring_within(3),
            "within_7_days": memberships_expiring_within(7),
        }
        return render(request, "reports/expiring.html", ctx)
