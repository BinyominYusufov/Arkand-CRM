"""Движок зарплаты (ЗРП-03…05). Схемы — data-driven, цифры не хардкодятся.

calculate_item поддерживает:
  fixed             — оклад;
  percent_of_sales  — base + процент от продаж (ЗРП-04);
  per_unit_tiered   — base + ставка за единицу со ступенями (ЗРП-05),
                      оба режима tier_mode: "flat" и "marginal".
Всё в Decimal, округление ROUND_HALF_UP до 2 знаков.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.exceptions import ConflictError, DomainError
from apps.finance.models import Transaction

from .models import Employee, PayrollItem, PayrollRun, SalaryScheme

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def _dec(value) -> Decimal:
    """JSON-число/строка → Decimal (не через float-репрезентацию)."""
    return Decimal(str(value))


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _tiered_bonus(config: dict, units: int) -> tuple[Decimal, list[dict]]:
    """ЗРП-05: бонус за единицы по ступеням.

    flat     — вся сумма по ставке достигнутого порога;
    marginal — ступенчато по диапазонам.
    """
    tiers = config.get("tiers") or []
    if not tiers:
        raise DomainError("Схема per_unit_tiered без tiers", code="invalid_scheme")
    mode = config.get("tier_mode", "flat")
    applied: list[dict] = []

    if mode == "flat":
        rate = None
        for tier in tiers:
            upto = tier.get("upto")
            if upto is None or units <= upto:
                rate = _dec(tier["rate"])
                break
        if rate is None:  # units выше всех порогов — последняя ставка
            rate = _dec(tiers[-1]["rate"])
        bonus = rate * units
        applied.append({"units": units, "rate": str(rate), "amount": str(_q(bonus))})
        return _q(bonus), applied

    if mode == "marginal":
        bonus = ZERO
        prev_upto = 0
        remaining = units
        for tier in tiers:
            upto = tier.get("upto")
            band = (upto - prev_upto) if upto is not None else remaining
            take = min(remaining, band) if band >= 0 else 0
            if take > 0:
                rate = _dec(tier["rate"])
                part = rate * take
                bonus += part
                applied.append(
                    {"units": take, "rate": str(rate), "amount": str(_q(part))}
                )
                remaining -= take
            if upto is not None:
                prev_upto = upto
            if remaining <= 0:
                break
        return _q(bonus), applied

    raise DomainError(f"Неизвестный tier_mode: {mode}", code="invalid_scheme")


def calculate_item(
    scheme: SalaryScheme, *, sales_amount: Decimal = ZERO, units: int = 0
) -> tuple[Decimal, Decimal, dict]:
    """Расчёт одной строки: (base, bonus, breakdown)."""
    config = scheme.config or {}
    base = _q(_dec(config.get("base", 0)))
    breakdown: dict = {
        "scheme_type": scheme.scheme_type,
        "base": str(base),
        "inputs": {"sales_amount": str(sales_amount), "units": units},
    }

    if scheme.scheme_type == SalaryScheme.SchemeType.FIXED:
        bonus = ZERO
    elif scheme.scheme_type == SalaryScheme.SchemeType.PERCENT_OF_SALES:
        percent = _dec(config.get("percent", 0))
        bonus = _q(_dec(sales_amount) * percent / Decimal("100"))
        breakdown["percent"] = str(percent)
    elif scheme.scheme_type == SalaryScheme.SchemeType.PER_UNIT_TIERED:
        bonus, applied = _tiered_bonus(config, units)
        breakdown["tier_mode"] = config.get("tier_mode", "flat")
        breakdown["unit"] = config.get("unit", "")
        breakdown["tiers_applied"] = applied
    else:
        raise DomainError(
            f"Неизвестный тип схемы: {scheme.scheme_type}", code="invalid_scheme"
        )

    breakdown["bonus"] = str(bonus)
    breakdown["total"] = str(_q(base + bonus))
    return base, bonus, breakdown


def _auto_inputs(employee: Employee, year: int, month: int) -> dict:
    """Автоввод при отсутствии явных данных: продажи бизнеса за месяц.

    sales_amount — сумма подтверждённых приходов бизнеса за период;
    units — число подтверждённых приходов (прокси «продаж» за штуку).
    Явные inputs в run_payroll имеют приоритет.
    """
    if not employee.business_id:
        return {"sales_amount": ZERO, "units": 0, "source": "none"}
    qs = Transaction.objects.confirmed().filter(
        business_id=employee.business_id,
        kind=Transaction.Kind.INCOME,
        occurred_at__year=year,
        occurred_at__month=month,
    )
    from django.db.models import Sum

    sales = _q(_dec(qs.aggregate(s=Sum("amount"))["s"] or 0))
    return {"sales_amount": sales, "units": qs.count(), "source": "auto"}


@transaction.atomic
def run_payroll(actor, *, year: int, month: int, inputs: dict | None = None) -> PayrollRun:
    """Расчёт зарплаты за период (ЗРП-01): синхронно, в сервисе.

    inputs: {employee_id: {"sales_amount": Decimal, "units": int}} — опционально.
    Повторный запуск для черновика пересчитывает строки; для утверждённого — ошибка.
    """
    inputs = inputs or {}
    run = PayrollRun.objects.filter(year=year, month=month).first()
    if run and run.status == PayrollRun.Status.FINALIZED:
        raise ConflictError("Расчёт за этот период уже утверждён")
    if run is None:
        run = PayrollRun.objects.create(year=year, month=month, created_by=actor)
    else:
        run.items.all().delete()  # пересчёт черновика

    employees = Employee.objects.filter(is_active=True).select_related("business")
    for employee in employees:
        scheme = employee.schemes.filter(is_active=True).order_by("-id").first()
        if scheme is None:
            continue
        emp_inputs = inputs.get(employee.pk) or inputs.get(str(employee.pk))
        if emp_inputs is not None:
            sales_amount = _dec(emp_inputs.get("sales_amount", 0))
            units = int(emp_inputs.get("units", 0))
            source = "manual"
        else:
            auto = _auto_inputs(employee, year, month)
            sales_amount, units, source = auto["sales_amount"], auto["units"], auto["source"]

        base, bonus, breakdown = calculate_item(
            scheme, sales_amount=sales_amount, units=units
        )
        breakdown["inputs"]["source"] = source
        PayrollItem.objects.create(
            run=run,
            employee=employee,
            base=base,
            bonus=bonus,
            total=_q(base + bonus),
            breakdown=breakdown,
        )

    AuditLog.record(
        actor,
        "payroll.run_calculated",
        run,
        after={
            "year": year,
            "month": month,
            "items": run.items.count(),
            "fund": str(sum((i.total for i in run.items.all()), ZERO)),
        },
    )
    return run


@transaction.atomic
def finalize_run(actor, *, run_id: int) -> PayrollRun:
    """Утверждение расчёта — условный UPDATE по статусу (идемпотентность)."""
    updated = PayrollRun.objects.filter(
        id=run_id, status=PayrollRun.Status.DRAFT
    ).update(status=PayrollRun.Status.FINALIZED, finalized_at=timezone.now())
    if updated == 0:
        raise ConflictError("Расчёт уже утверждён или не найден")
    run = PayrollRun.objects.get(id=run_id)
    AuditLog.record(
        actor,
        "payroll.run_finalized",
        run,
        before={"status": PayrollRun.Status.DRAFT},
        after={"status": run.status},
    )
    return run
