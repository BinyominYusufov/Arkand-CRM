"""Селекторы взаиморасчётов (БАР-02, ФНС-12, ХОЛ-33 «просрочен»)."""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .holding_rules import HOLDING_RULES
from .models import Debt

ZERO = Decimal("0.00")


def debt_remaining_map(debts) -> dict[int, Decimal]:
    """Остатки по долгам одним запросом (без N+1)."""
    from .models import DebtSettlement

    settled = {
        row["debt_id"]: row["s"] or ZERO
        for row in DebtSettlement.objects.filter(debt__in=debts)
        .values("debt_id")
        .annotate(s=Sum("amount"))
    }
    return {d.pk: d.amount - settled.get(d.pk, ZERO) for d in debts}


def is_debt_overdue(debt: Debt, *, now=None) -> bool:
    """ХОЛ-33: открытый долг «просрочен» после N дней (0 = не помечать)."""
    days = HOLDING_RULES["debt_overdue_days"]
    if not days or debt.status != Debt.Status.OPEN:
        return False
    now = now or timezone.now()
    return debt.created_at < now - timedelta(days=days)


def debts_registry() -> dict:
    """БАР-02/ФНС-12: прозрачный реестр «кто кому должен».

    Возвращает открытые долги с остатками и попарную сводку.
    """
    open_debts = list(
        Debt.objects.filter(status=Debt.Status.OPEN)
        .select_related("debtor", "creditor", "source_transfer")
        .order_by("created_at")
    )
    remaining = debt_remaining_map(open_debts)

    pairs: dict[tuple[int, int], dict] = {}
    rows = []
    for d in open_debts:
        rem = remaining[d.pk]
        if rem <= 0:
            continue
        rows.append(
            {
                "id": d.pk,
                "debtor_id": d.debtor_id,
                "debtor_name": d.debtor.name,
                "creditor_id": d.creditor_id,
                "creditor_name": d.creditor.name,
                "amount": d.amount,
                "remaining": rem,
                "is_overdue": is_debt_overdue(d),
                "created_at": d.created_at,
                "source_transfer_id": d.source_transfer_id,
            }
        )
        key = (d.debtor_id, d.creditor_id)
        if key not in pairs:
            pairs[key] = {
                "debtor_id": d.debtor_id,
                "debtor_name": d.debtor.name,
                "creditor_id": d.creditor_id,
                "creditor_name": d.creditor.name,
                "total_remaining": ZERO,
                "debts_count": 0,
            }
        pairs[key]["total_remaining"] += rem
        pairs[key]["debts_count"] += 1

    return {
        "debts": rows,
        "pairs": sorted(
            pairs.values(), key=lambda p: p["total_remaining"], reverse=True
        ),
        "total_open": sum((r["remaining"] for r in rows), ZERO),
    }
