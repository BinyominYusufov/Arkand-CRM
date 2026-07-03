from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/finance/", include("apps.finance.urls")),
    path("api/v1/cash/", include("apps.cash.urls")),
    path("api/v1/settlements/", include("apps.settlements.urls")),
    path("api/v1/payroll/", include("apps.payroll.urls")),
    path("api/v1/reports/", include("apps.reports.urls")),
    path("api/v1/overlay/", include("apps.overlay.urls")),
    path("api/v1/audit/", include("apps.audit.urls")),
]
