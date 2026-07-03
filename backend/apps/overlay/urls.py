from django.urls import path

from .views import (
    OverlayCashView,
    OverlayDebtsView,
    OverlayExportView,
    OverlayPayrollView,
    OverlaySummaryView,
)

urlpatterns = [
    path("summary", OverlaySummaryView.as_view(), name="overlay-summary"),
    path("cash", OverlayCashView.as_view(), name="overlay-cash"),
    path("debts", OverlayDebtsView.as_view(), name="overlay-debts"),
    path("payroll", OverlayPayrollView.as_view(), name="overlay-payroll"),
    path("export", OverlayExportView.as_view(), name="overlay-export"),
]
