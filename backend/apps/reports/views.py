"""Отчёты ФНС-10…13: тонкие вьюхи над селекторами; деньги — строкой."""
from decimal import Decimal

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.money import q2
from apps.core.permissions import CanViewReports

from . import selectors


def money_str(value) -> str:
    """Деньги в JSON — строкой с ровно 2 знаками (не зависит от СУБД)."""
    if isinstance(value, (Decimal, int, float)):
        return str(q2(value))
    return str(value)


def serialize_money(obj, keys: tuple[str, ...]) -> None:
    for k in keys:
        if k in obj and obj[k] is not None:
            obj[k] = money_str(obj[k])


class CashflowReportView(APIView):
    """ФНС-10: поступления и расходы по бизнесам и сводно."""

    permission_classes = [IsAuthenticated, CanViewReports]

    def get(self, request):
        data = selectors.cashflow_report(
            date_from=request.query_params.get("date_from") or None,
            date_to=request.query_params.get("date_to") or None,
        )
        for row in data["businesses"]:
            serialize_money(row, ("income", "expense", "profit"))
        data["total"] = {k: money_str(v) for k, v in data["total"].items()}
        return Response(data)


class CashflowMonthlyView(APIView):
    """Помесячная динамика для графиков (6 месяцев по умолчанию)."""

    permission_classes = [IsAuthenticated, CanViewReports]

    def get(self, request):
        try:
            months = min(int(request.query_params.get("months", 6)), 24)
        except ValueError:
            months = 6
        rows = selectors.cashflow_monthly(months=months)
        for row in rows:
            serialize_money(row, ("income", "expense"))
        return Response({"months": months, "rows": rows})


class ExpenseByCategoryView(APIView):
    """Структура расходов по категориям."""

    permission_classes = [IsAuthenticated, CanViewReports]

    def get(self, request):
        rows = selectors.expense_by_category(
            date_from=request.query_params.get("date_from") or None,
            date_to=request.query_params.get("date_to") or None,
        )
        for row in rows:
            serialize_money(row, ("total",))
        return Response({"rows": rows})


class CashRegistersReportView(APIView):
    """ФНС-11: кассы — остатки и обороты (только финотдел/владельцы)."""

    permission_classes = [IsAuthenticated, CanViewReports]

    def get(self, request):
        data = selectors.cash_registers_report()
        for row in data["registers"]:
            serialize_money(row, ("balance", "month_turnover", "turnover_limit"))
        serialize_money(data, ("total_balance", "total_month_turnover"))
        return Response(data)


class DebtsReportView(APIView):
    """ФНС-12: взаиморасчёты и долги между бизнесами."""

    permission_classes = [IsAuthenticated, CanViewReports]

    def get(self, request):
        data = selectors.debts_report()
        for row in data["debts"]:
            serialize_money(row, ("amount", "remaining"))
        for pair in data["pairs"]:
            serialize_money(pair, ("total_remaining",))
        serialize_money(data, ("total_open",))
        return Response(data)


class PayrollReportView(APIView):
    """ФНС-13: зарплатный фонд; прибыль по бизнесам и холдингу."""

    permission_classes = [IsAuthenticated, CanViewReports]

    def get(self, request):
        from apps.core.exceptions import DomainError

        year = request.query_params.get("year")
        month = request.query_params.get("month")
        try:
            year_i = int(year) if year else None
            month_i = int(month) if month else None
        except ValueError:
            raise DomainError(
                "year и month должны быть числами", code="validation_error"
            )
        data = selectors.payroll_report(year=year_i, month=month_i)
        for row in data["fund_by_business"]:
            serialize_money(row, ("base", "bonus", "fund"))
        serialize_money(data, ("fund_total",))
        for row in data["profit_by_business"]:
            serialize_money(row, ("income", "expense", "profit"))
        data["profit_total"] = {k: money_str(v) for k, v in data["profit_total"].items()}
        for run in data["runs"]:
            serialize_money(run, ("fund",))
        return Response(data)
