"""Селекторы касс. Изоляция КАС-04 — на уровне queryset."""
from decimal import Decimal

from django.db.models import Case, DecimalField, F, Sum, When

from apps.core import rbac
from apps.core.money import q2

from .models import CashOperation, CashRegister

ZERO = Decimal("0.00")


def registers_for_user(user):
    """Кассир видит только свои кассы; финотдел/владельцы — все (КАС-04)."""
    qs = CashRegister.objects.select_related("business").filter(is_active=True)
    if rbac.user_has_perm(user, rbac.PERM_CASH_VIEW_ALL):
        return qs
    return qs.filter(members=user)


def operations_for_user(user):
    return (
        CashOperation.objects.alive()
        .filter(register__in=registers_for_user(user))
        .select_related("register", "register__business", "created_by")
    )


def register_balance(register: CashRegister) -> Decimal:
    """КАС-02: остаток = сумма операций (in − out)."""
    agg = register.operations.alive().aggregate(
        balance=Sum(
            Case(
                When(direction=CashOperation.Direction.IN, then=F("amount")),
                When(direction=CashOperation.Direction.OUT, then=-F("amount")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
    )
    return q2(agg["balance"])


def register_month_turnover(register: CashRegister, year: int, month: int) -> Decimal:
    """Оборот кассы за календарный месяц (in + out) — для лимита КАС-03."""
    agg = register.operations.alive().filter(
        occurred_at__year=year, occurred_at__month=month
    ).aggregate(s=Sum("amount"))
    return q2(agg["s"])


def register_overview(register: CashRegister, *, year: int, month: int) -> dict:
    balance = register_balance(register)
    turnover = register_month_turnover(register, year, month)
    limit = register.turnover_limit
    return {
        "id": register.id,
        "name": register.name,
        "business_id": register.business_id,
        "business_name": register.business.name,
        "balance": balance,
        "month_turnover": turnover,
        "turnover_limit": limit,
        "limit_utilization": (
            float(turnover / limit * 100) if limit and limit > 0 else 0.0
        ),
        "over_limit": bool(limit and limit > 0 and turnover > limit),
    }
