import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from apps.reports.services import dashboard_summary


class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        date_str = request.GET.get("date")
        try:
            as_of = datetime.date.fromisoformat(date_str) if date_str else timezone.localdate()
        except ValueError:
            as_of = timezone.localdate()
        ctx = {"summary": dashboard_summary(as_of), "as_of": as_of}
        return render(request, "dashboard/index.html", ctx)
