"""Тесты долгов: settle_debt (БАР-03), is_debt_overdue (ХОЛ-33), реестр (БАР-02)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.exceptions import ConflictError, DomainError
from apps.settlements import selectors, services
from apps.settlements.models import Debt, DebtSettlement
from apps.testing import factories as f

pytestmark = pytest.mark.django_db


# --- settle_debt (БАР-03) ---
def test_settle_full_closes_debt(accountant):
    debt = f.DebtFactory(amount=Decimal("5000.00"))
    settlement = services.settle_debt(
        accountant,
        debt_id=debt.pk,
        method=DebtSettlement.Method.RETURN,
        amount=Decimal("5000.00"),
    )
    assert settlement.amount == Decimal("5000.00")
    assert settlement.method == DebtSettlement.Method.RETURN
    assert settlement.created_by == accountant

    debt.refresh_from_db()
    assert debt.status == Debt.Status.CLOSED
    assert debt.closed_at is not None
    assert services.debt_remaining(debt) == Decimal("0.00")

    log = AuditLog.objects.get(action="debt.settled", entity_id=str(debt.pk))
    assert log.before == {"remaining": "5000.00", "status": "open"}
    assert log.after["remaining"] == "0.00"
    assert log.after["status"] == "closed"
    assert log.after["method"] == "return"


def test_settle_partial_keeps_debt_open(accountant):
    debt = f.DebtFactory(amount=Decimal("5000.00"))
    services.settle_debt(
        accountant,
        debt_id=debt.pk,
        method=DebtSettlement.Method.OFFSET,
        amount=Decimal("1500.00"),
    )
    debt.refresh_from_db()
    assert debt.status == Debt.Status.OPEN
    assert debt.closed_at is None
    assert services.debt_remaining(debt) == Decimal("3500.00")

    log = AuditLog.objects.get(action="debt.settled", entity_id=str(debt.pk))
    assert log.after["remaining"] == "3500.00"
    assert log.after["status"] == "open"

    # Второе частичное погашение: остаток продолжает уменьшаться.
    services.settle_debt(
        accountant,
        debt_id=debt.pk,
        method=DebtSettlement.Method.RETURN,
        amount=Decimal("500.00"),
    )
    debt.refresh_from_db()
    assert debt.status == Debt.Status.OPEN
    assert services.debt_remaining(debt) == Decimal("3000.00")


def test_settle_exceeds_remaining_rejected(accountant):
    debt = f.DebtFactory(amount=Decimal("5000.00"))
    services.settle_debt(
        accountant,
        debt_id=debt.pk,
        method=DebtSettlement.Method.RETURN,
        amount=Decimal("4000.00"),
    )
    with pytest.raises(DomainError) as exc:
        services.settle_debt(
            accountant,
            debt_id=debt.pk,
            method=DebtSettlement.Method.RETURN,
            amount=Decimal("1000.01"),
        )
    assert exc.value.code == "settlement_exceeds_debt"
    assert exc.value.details == {"remaining": "1000.00", "attempted": "1000.01"}
    # Погашение сверх остатка не записано.
    assert debt.settlements.count() == 1


def test_settle_closed_debt_conflict(accountant):
    debt = f.DebtFactory(amount=Decimal("100.00"))
    services.settle_debt(
        accountant, debt_id=debt.pk, method=DebtSettlement.Method.RETURN
    )
    with pytest.raises(ConflictError):
        services.settle_debt(
            accountant,
            debt_id=debt.pk,
            method=DebtSettlement.Method.RETURN,
            amount=Decimal("1.00"),
        )


def test_settle_amount_none_closes_remainder(accountant):
    debt = f.DebtFactory(amount=Decimal("5000.00"))
    services.settle_debt(
        accountant,
        debt_id=debt.pk,
        method=DebtSettlement.Method.RETURN,
        amount=Decimal("2000.00"),
    )
    settlement = services.settle_debt(
        accountant, debt_id=debt.pk, method=DebtSettlement.Method.OFFSET, amount=None
    )
    assert settlement.amount == Decimal("3000.00")
    debt.refresh_from_db()
    assert debt.status == Debt.Status.CLOSED
    assert services.debt_remaining(debt) == Decimal("0.00")


def test_settle_missing_debt_conflict(accountant):
    with pytest.raises(ConflictError):
        services.settle_debt(
            accountant, debt_id=999999, method=DebtSettlement.Method.RETURN
        )


def test_settle_nonpositive_amount_rejected(accountant):
    debt = f.DebtFactory(amount=Decimal("100.00"))
    with pytest.raises(DomainError) as exc:
        services.settle_debt(
            accountant,
            debt_id=debt.pk,
            method=DebtSettlement.Method.RETURN,
            amount=Decimal("-5.00"),
        )
    assert exc.value.code == "invalid_amount"


# --- is_debt_overdue (ХОЛ-33) ---
def _age_debt(debt: Debt, days: int) -> Debt:
    Debt.objects.filter(pk=debt.pk).update(
        created_at=timezone.now() - timedelta(days=days)
    )
    debt.refresh_from_db()
    return debt


def test_overdue_open_old_debt():
    debt = _age_debt(f.DebtFactory(), days=31)
    assert selectors.is_debt_overdue(debt) is True


def test_overdue_fresh_debt_false():
    debt = f.DebtFactory()
    assert selectors.is_debt_overdue(debt) is False


def test_overdue_closed_old_debt_false(accountant):
    debt = f.DebtFactory(amount=Decimal("100.00"))
    services.settle_debt(
        accountant, debt_id=debt.pk, method=DebtSettlement.Method.RETURN
    )
    debt = _age_debt(debt, days=31)
    assert debt.status == Debt.Status.CLOSED
    assert selectors.is_debt_overdue(debt) is False


def test_overdue_disabled_when_days_zero(monkeypatch):
    monkeypatch.setitem(selectors.HOLDING_RULES, "debt_overdue_days", 0)
    debt = _age_debt(f.DebtFactory(), days=365)
    assert selectors.is_debt_overdue(debt) is False


# --- debts_registry (БАР-02) ---
def test_debts_registry_remaining_pairs_and_total(accountant):
    b1, b2, b3 = f.BusinessFactory(), f.BusinessFactory(), f.BusinessFactory()

    d1 = f.DebtFactory(debtor=b1, creditor=b2, amount=Decimal("10000.00"))
    services.settle_debt(
        accountant,
        debt_id=d1.pk,
        method=DebtSettlement.Method.RETURN,
        amount=Decimal("4000.00"),
    )
    d2 = f.DebtFactory(debtor=b1, creditor=b2, amount=Decimal("5000.00"))
    d3 = f.DebtFactory(debtor=b3, creditor=b1, amount=Decimal("7000.00"))

    # Закрытый долг в реестр не попадает.
    d_closed = f.DebtFactory(debtor=b2, creditor=b3, amount=Decimal("999.00"))
    services.settle_debt(
        accountant, debt_id=d_closed.pk, method=DebtSettlement.Method.RETURN
    )
    # Открытый долг с нулевым остатком (погашен напрямую) — тоже скрыт.
    d_zero = f.DebtFactory(debtor=b2, creditor=b1, amount=Decimal("300.00"))
    DebtSettlement.objects.create(
        debt=d_zero, method=DebtSettlement.Method.RETURN, amount=Decimal("300.00")
    )

    data = selectors.debts_registry()

    rows = {r["id"]: r for r in data["debts"]}
    assert set(rows) == {d1.pk, d2.pk, d3.pk}
    assert rows[d1.pk]["remaining"] == Decimal("6000.00")
    assert rows[d1.pk]["amount"] == Decimal("10000.00")
    assert rows[d1.pk]["debtor_id"] == b1.pk
    assert rows[d1.pk]["creditor_id"] == b2.pk
    assert rows[d1.pk]["is_overdue"] is False
    assert rows[d2.pk]["remaining"] == Decimal("5000.00")
    assert rows[d3.pk]["remaining"] == Decimal("7000.00")

    # Пары агрегируются: b1→b2 объединяет два долга.
    pairs = {(p["debtor_id"], p["creditor_id"]): p for p in data["pairs"]}
    assert set(pairs) == {(b1.pk, b2.pk), (b3.pk, b1.pk)}
    assert pairs[(b1.pk, b2.pk)]["total_remaining"] == Decimal("11000.00")
    assert pairs[(b1.pk, b2.pk)]["debts_count"] == 2
    assert pairs[(b3.pk, b1.pk)]["total_remaining"] == Decimal("7000.00")
    assert pairs[(b3.pk, b1.pk)]["debts_count"] == 1
    # Сортировка пар — по убыванию остатка.
    assert data["pairs"][0]["total_remaining"] == Decimal("11000.00")

    assert data["total_open"] == Decimal("18000.00")


def test_debts_registry_empty():
    data = selectors.debts_registry()
    assert data["debts"] == []
    assert data["pairs"] == []
    assert data["total_open"] == Decimal("0.00")


def test_debts_registry_marks_overdue():
    debt = _age_debt(f.DebtFactory(amount=Decimal("100.00")), days=45)
    data = selectors.debts_registry()
    row = next(r for r in data["debts"] if r["id"] == debt.pk)
    assert row["is_overdue"] is True
