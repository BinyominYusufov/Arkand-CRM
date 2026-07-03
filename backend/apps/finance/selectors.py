"""Селекторы финансов — только чтение (ФНС-03, ФНС-04)."""
from decimal import Decimal

from django.db.models import Q, Sum

from apps.core import rbac
from apps.core.models import Business
from apps.core.money import q2

from .models import Transaction

ZERO = Decimal("0.00")


def transactions_for_user(user):
    """Операции, видимые пользователю.

    Изоляция на уровне данных: queryset режется по доступным бизнесам
    (Часть 0, BusinessAccess) — «чужое» физически не попадает в ответ.
    """
    businesses = rbac.accessible_businesses(user)
    return (
        Transaction.objects.alive()
        .filter(business__in=businesses)
        .select_related("business", "category", "confirmed_by", "created_by")
    )


def _period_filter(date_from=None, date_to=None) -> Q:
    q = Q()
    if date_from:
        q &= Q(occurred_at__date__gte=date_from)
    if date_to:
        q &= Q(occurred_at__date__lte=date_to)
    return q


def profit_for_business(business: Business, *, date_from=None, date_to=None) -> dict:
    """ФНС-04: прибыль бизнеса за период = доходы − расходы (confirmed)."""
    qs = Transaction.objects.confirmed().filter(business=business)
    qs = qs.filter(_period_filter(date_from, date_to))
    income = q2(qs.filter(kind=Transaction.Kind.INCOME).aggregate(s=Sum("amount"))["s"])
    expense = q2(qs.filter(kind=Transaction.Kind.EXPENSE).aggregate(s=Sum("amount"))["s"])
    return {
        "business_id": business.id,
        "business_name": business.name,
        "income": income,
        "expense": expense,
        "profit": income - expense,
    }


def profit_by_business(*, date_from=None, date_to=None, businesses=None) -> dict:
    """Прибыль по каждому бизнесу и сводно по холдингу."""
    if businesses is None:
        businesses = Business.objects.filter(is_active=True)
    rows = [
        profit_for_business(b, date_from=date_from, date_to=date_to) for b in businesses
    ]
    return {
        "businesses": rows,
        "total": {
            "income": sum((r["income"] for r in rows), ZERO),
            "expense": sum((r["expense"] for r in rows), ZERO),
            "profit": sum((r["profit"] for r in rows), ZERO),
        },
    }
