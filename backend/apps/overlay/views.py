"""Часть 7 (провизорно): консолидация для владельцев.

Только чтение поверх финмодуля; агрегаты — из reports-селекторов
(логика не дублируется). Доступ — только роль owner (overlay.view).

# TODO: согласовать формат экспорта с реальной Частью 7.
"""
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import OwnerOverlay
from apps.reports import selectors as reports_selectors
from apps.reports.views import money_str, serialize_money

# Версия контракта экспорта — точка стыковки с реальной Частью 7.
EXPORT_FORMAT = "arkand.overlay"
EXPORT_VERSION = 1


def _summary_payload(date_from=None, date_to=None) -> dict:
    data = reports_selectors.holding_summary(date_from=date_from, date_to=date_to)
    for row in data["businesses"]:
        serialize_money(row, ("income", "expense", "profit"))
    data["total"] = {k: money_str(v) for k, v in data["total"].items()}
    serialize_money(data, ("open_debts_total", "cash_balance_total"))
    return data


def _cash_payload() -> dict:
    data = reports_selectors.cash_registers_report()
    for row in data["registers"]:
        serialize_money(row, ("balance", "month_turnover", "turnover_limit"))
    serialize_money(data, ("total_balance", "total_month_turnover"))
    return data


def _debts_payload() -> dict:
    data = reports_selectors.debts_report()
    for row in data["debts"]:
        serialize_money(row, ("amount", "remaining"))
    for pair in data["pairs"]:
        serialize_money(pair, ("total_remaining",))
    serialize_money(data, ("total_open",))
    return data


def _payroll_payload() -> dict:
    data = reports_selectors.payroll_report()
    for row in data["fund_by_business"]:
        serialize_money(row, ("base", "bonus", "fund"))
    serialize_money(data, ("fund_total",))
    for row in data["profit_by_business"]:
        serialize_money(row, ("income", "expense", "profit"))
    data["profit_total"] = {k: money_str(v) for k, v in data["profit_total"].items()}
    for run in data["runs"]:
        serialize_money(run, ("fund",))
    return data


class OverlaySummaryView(APIView):
    """Свод по холдингу: доходы/расходы/прибыль сводно и по бизнесам."""

    permission_classes = [IsAuthenticated, OwnerOverlay]

    def get(self, request):
        return Response(
            _summary_payload(
                request.query_params.get("date_from") or None,
                request.query_params.get("date_to") or None,
            )
        )


class OverlayCashView(APIView):
    """Кассы всего холдинга (ФНС-11)."""

    permission_classes = [IsAuthenticated, OwnerOverlay]

    def get(self, request):
        return Response(_cash_payload())


class OverlayDebtsView(APIView):
    """Полный граф «кто кому должен» (ФНС-12)."""

    permission_classes = [IsAuthenticated, OwnerOverlay]

    def get(self, request):
        return Response(_debts_payload())


class OverlayPayrollView(APIView):
    """Зарплатный фонд по холдингу (ФНС-13)."""

    permission_classes = [IsAuthenticated, OwnerOverlay]

    def get(self, request):
        return Response(_payroll_payload())


class OverlayExportView(APIView):
    """Экспорт консолидации — стабильный версионируемый JSON-контракт."""

    permission_classes = [IsAuthenticated, OwnerOverlay]

    def get(self, request):
        return Response(
            {
                "format": EXPORT_FORMAT,
                "version": EXPORT_VERSION,
                "generated_at": timezone.now().isoformat(),
                "generated_for": request.user.email,
                "data": {
                    "summary": _summary_payload(),
                    "cash": _cash_payload(),
                    "debts": _debts_payload(),
                    "payroll": _payroll_payload(),
                },
            }
        )
