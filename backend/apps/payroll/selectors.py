"""Селекторы зарплаты (ФНС-13: зарплатный фонд)."""
from decimal import Decimal

from django.db.models import Sum

from apps.core.money import q2

from .models import PayrollItem, PayrollRun

ZERO = Decimal("0.00")


def payroll_fund_by_business(run: PayrollRun) -> list[dict]:
    """Фонд по бизнесам в рамках одного расчёта (None → головной офис)."""
    rows = (
        PayrollItem.objects.filter(run=run)
        .values("employee__business_id", "employee__business__name")
        .annotate(fund=Sum("total"), base=Sum("base"), bonus=Sum("bonus"))
        .order_by("employee__business__name")
    )
    return [
        {
            "business_id": r["employee__business_id"],
            "business_name": r["employee__business__name"] or "Головной офис",
            "base": q2(r["base"]),
            "bonus": q2(r["bonus"]),
            "fund": q2(r["fund"]),
        }
        for r in rows
    ]


def run_total(run: PayrollRun) -> Decimal:
    return q2(PayrollItem.objects.filter(run=run).aggregate(s=Sum("total"))["s"])


def latest_run(*, finalized_only: bool = False) -> PayrollRun | None:
    qs = PayrollRun.objects.all()
    if finalized_only:
        qs = qs.filter(status=PayrollRun.Status.FINALIZED)
    return qs.order_by("-year", "-month").first()
