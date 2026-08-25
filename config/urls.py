from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("members/", include("apps.members.urls")),
    path("memberships/", include("apps.memberships.urls")),
    path("attendance/", include("apps.attendance.urls")),
    path("sales/", include("apps.sales.urls")),
    path("billing/", include("apps.billing.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("reports/", include("apps.reports.urls")),
    path("api/", include("apps.members.api_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
