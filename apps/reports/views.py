import datetime
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
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


class AnalyticsView(LoginRequiredMixin, View):
    """Chart.js-powered analytics dashboard — trend charts, pie charts, bar charts."""

    VALID_DAYS = {7, 30, 90}

    def get(self, request):
        try:
            days = int(request.GET.get("days", 30))
        except (ValueError, TypeError):
            days = 30
        if days not in self.VALID_DAYS:
            days = 30

        today = timezone.localdate()
        start = today - datetime.timedelta(days=days - 1)

        rev_trend = services.revenue_trend(days)
        att_trend = services.attendance_trend(days)
        mem_status = services.membership_status_breakdown()
        pay_methods = services.payment_method_breakdown(days)
        top_products = list(services.best_selling_products(start, today, limit=10))
        low_stock = list(services.low_stock_products().values("name", "stock_quantity", "low_stock_threshold"))

        # Serialize everything as JSON for safe embedding in the template
        charts = {
            "revenueTrend": {
                "labels": [r["date"] for r in rev_trend],
                "data": [r["total"] for r in rev_trend],
            },
            "attendanceTrend": {
                "labels": [a["date"] for a in att_trend],
                "data": [a["count"] for a in att_trend],
            },
            "membershipStatus": {
                "labels": [m["label"] for m in mem_status],
                "data": [m["count"] for m in mem_status],
            },
            "paymentMethods": {
                "labels": [p["label"] for p in pay_methods],
                "data": [p["total"] for p in pay_methods],
            },
            "topProducts": {
                "labels": [p["product__name"] for p in top_products],
                "revenue": [float(p["revenue"] or 0) for p in top_products],
                "qty": [float(p["quantity_sold"] or 0) for p in top_products],
            },
            "lowStock": {
                "labels": [p["name"] for p in low_stock],
                "stock": [float(p["stock_quantity"]) for p in low_stock],
                "threshold": [float(p["low_stock_threshold"]) for p in low_stock],
            },
        }

        ctx = {
            "days": days,
            "charts": charts,
        }
        return render(request, "reports/analytics.html", ctx)

