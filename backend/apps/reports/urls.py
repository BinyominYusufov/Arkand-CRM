from django.urls import path

from .views import (
    CashflowMonthlyView,
    CashflowReportView,
    CashRegistersReportView,
    DebtsReportView,
    ExpenseByCategoryView,
    PayrollReportView,
)

urlpatterns = [
    path("cashflow", CashflowReportView.as_view(), name="report-cashflow"),
    path("cashflow/monthly", CashflowMonthlyView.as_view(), name="report-cashflow-monthly"),
    path("expenses/by-category", ExpenseByCategoryView.as_view(), name="report-expense-category"),
    path("cash-registers", CashRegistersReportView.as_view(), name="report-cash-registers"),
    path("debts", DebtsReportView.as_view(), name="report-debts"),
    path("payroll", PayrollReportView.as_view(), name="report-payroll"),
]
