from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("daily/", views.DailyReportView.as_view(), name="daily"),
    path("monthly/", views.MonthlyReportView.as_view(), name="monthly"),
    path("products/", views.ProductReportView.as_view(), name="products"),
    path("expiring/", views.ExpiringMembershipsView.as_view(), name="expiring"),
]
