"""Селекторы сводных отчётов (ФНС-10…13).

Переиспользуются overlay-надстройкой Части 7 — логика не дублируется.
"""
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.cash import selectors as cash_selectors
from apps.cash.models import CashRegister
from apps.core.models import Business
from apps.finance import selectors as finance_selectors
from apps.finance.models import Transaction
from apps.payroll import selectors as payroll_selectors
from apps.payroll.models import PayrollRun
from apps.settlements import selectors as settlements_selectors

ZERO = Decimal("0.00")


def cashflow_report(*, date_from=None, date_to=None) -> dict:
    """ФНС-10: поступления и расходы по бизнесам и сводно."""
    return finance_selectors.profit_by_business(date_from=date_from, date_to=date_to)


def cashflow_monthly(*, months: int = 6) -> list[dict]:
    """Помесячная динамика для графиков: доход/расход по бизнесам."""
    now = timezone.localtime()
    # Первое число месяца (months-1) назад.
    year, month = now.year, now.month
    total = year * 12 + (month - 1) - (months - 1)
    start_year, start_month = divmod(total, 12)
    start = now.replace(
        year=start_year, month=start_month + 1, day=1,
        hour=0, minute=0, second=0, microsecond=0,
    )
    rows = (
        Transaction.objects.confirmed()
        .filter(occurred_at__gte=start)
        .annotate(month_dt=TruncMonth("occurred_at"))
        .values("month_dt", "business_id", "business__name", "kind")
        .annotate(total=Sum("amount"))
        .order_by("month_dt")
    )
    result: dict[tuple, dict] = {}
    for r in rows:
        key = (r["month_dt"], r["business_id"])
        entry = result.setdefault(
            key,
            {
                "month": r["month_dt"].strftime("%Y-%m"),
                "business_id": r["business_id"],
                "business_name": r["business__name"],
                "income": ZERO,
                "expense": ZERO,
            },
        )
        if r["kind"] == Transaction.Kind.INCOME:
            entry["income"] = r["total"] or ZERO
        else:
            entry["expense"] = r["total"] or ZERO
    return list(result.values())


def expense_by_category(*, date_from=None, date_to=None) -> list[dict]:
    """Структура расходов по категориям (для отчётов и графиков)."""
    qs = Transaction.objects.confirmed().filter(kind=Transaction.Kind.EXPENSE)
    if date_from:
        qs = qs.filter(occurred_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(occurred_at__date__lte=date_to)
    rows = (
        qs.values("category_id", "category__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    return [
        {
            "category_id": r["category_id"],
            "category_name": r["category__name"] or "Без категории",
            "total": r["total"] or ZERO,
            "count": r["count"],
        }
        for r in rows
    ]


def cash_registers_report() -> dict:
    """ФНС-11: кассы — остатки и обороты (только финотдел/владельцы)."""
    now = timezone.localtime()
    registers = CashRegister.objects.select_related("business").filter(is_active=True)
    rows = [
        cash_selectors.register_overview(r, year=now.year, month=now.month)
        for r in registers
    ]
    return {
        "registers": rows,
        "total_balance": sum((r["balance"] for r in rows), ZERO),
        "total_month_turnover": sum((r["month_turnover"] for r in rows), ZERO),
    }


def debts_report() -> dict:
    """ФНС-12: взаиморасчёты и долги между бизнесами."""
    return settlements_selectors.debts_registry()


def payroll_report(*, year: int | None = None, month: int | None = None) -> dict:
    """ФНС-13: зарплатный фонд + прибыль по бизнесам и холдингу."""
    run = None
    if year and month:
        run = PayrollRun.objects.filter(year=year, month=month).first()
    if run is None:
        run = payroll_selectors.latest_run()

    fund_rows, fund_total, period = [], ZERO, None
    if run is not None:
        fund_rows = payroll_selectors.payroll_fund_by_business(run)
        fund_total = payroll_selectors.run_total(run)
        period = {"year": run.year, "month": run.month, "status": run.status}

    # Прибыль за тот же период (или за всё время, если расчётов нет).
    date_from = date_to = None
    if run is not None:
        import calendar

        date_from = f"{run.year:04d}-{run.month:02d}-01"
        last_day = calendar.monthrange(run.year, run.month)[1]
        date_to = f"{run.year:04d}-{run.month:02d}-{last_day:02d}"
    profit = finance_selectors.profit_by_business(date_from=date_from, date_to=date_to)

    return {
        "period": period,
        "fund_by_business": fund_rows,
        "fund_total": fund_total,
        "profit_by_business": profit["businesses"],
        "profit_total": profit["total"],
        "runs": [
            {
                "id": r.pk,
                "year": r.year,
                "month": r.month,
                "status": r.status,
                "fund": payroll_selectors.run_total(r),
            }
            for r in PayrollRun.objects.order_by("-year", "-month")[:12]
        ],
    }


def holding_summary(*, date_from=None, date_to=None) -> dict:
    """Свод по холдингу для Части 7: KPI + разбивка по бизнесам."""
    profit = finance_selectors.profit_by_business(date_from=date_from, date_to=date_to)
    debts = debts_report()
    cash = cash_registers_report()
    return {
        "businesses": profit["businesses"],
        "total": profit["total"],
        "open_debts_total": debts["total_open"],
        "cash_balance_total": cash["total_balance"],
        "businesses_count": Business.objects.filter(is_active=True).count(),
    }
