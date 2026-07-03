"""Тесты неттинга (ХОЛ-31) и бартера (БАР-04, ХОЛ-33)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.exceptions import ConflictError, DomainError, NotAllowedError
from apps.settlements import services
from apps.settlements.models import Barter, Debt, DebtSettlement
from apps.testing import factories as f

pytestmark = pytest.mark.django_db


# --- net_debts (ХОЛ-31) ---
def test_net_debts_bilateral(accountant):
    a, b = f.BusinessFactory(), f.BusinessFactory()
    debt_ab = f.DebtFactory(debtor=a, creditor=b, amount=Decimal("30000.00"))
    debt_ba = f.DebtFactory(debtor=b, creditor=a, amount=Decimal("18000.00"))

    result = services.net_debts(accountant, business_a=a, business_b=b)

    assert result["netted_amount"] == Decimal("18000.00")
    assert result["remaining_a_to_b"] == Decimal("12000.00")
    assert result["remaining_b_to_a"] == Decimal("0.00")

    debt_ab.refresh_from_db()
    debt_ba.refresh_from_db()
    # Меньший встречный долг закрыт полностью.
    assert debt_ba.status == Debt.Status.CLOSED
    assert debt_ba.closed_at is not None
    # Больший остаётся открытым с уменьшенным остатком.
    assert debt_ab.status == Debt.Status.OPEN
    assert services.debt_remaining(debt_ab) == Decimal("12000.00")

    # Погашения — взаимозачётом.
    methods = set(
        DebtSettlement.objects.filter(debt__in=[debt_ab, debt_ba]).values_list(
            "method", flat=True
        )
    )
    assert methods == {DebtSettlement.Method.OFFSET}

    log = AuditLog.objects.get(action="debts.netted")
    assert log.entity_type == "Business"
    assert log.entity_id == str(a.pk)
    assert log.after["netted_amount"] == "18000.00"
    assert log.after["remaining_a_to_b"] == "12000.00"
    assert log.after["remaining_b_to_a"] == "0.00"
    # Каждое погашение при неттинге тоже в аудите.
    assert AuditLog.objects.filter(action="debt.settled").count() == 2


def test_net_debts_settles_oldest_first(accountant):
    a, b = f.BusinessFactory(), f.BusinessFactory()
    old = f.DebtFactory(debtor=a, creditor=b, amount=Decimal("10000.00"))
    new = f.DebtFactory(debtor=a, creditor=b, amount=Decimal("20000.00"))
    Debt.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=5))
    Debt.objects.filter(pk=new.pk).update(created_at=timezone.now() - timedelta(days=1))
    counter = f.DebtFactory(debtor=b, creditor=a, amount=Decimal("15000.00"))

    result = services.net_debts(accountant, business_a=a, business_b=b)
    assert result["netted_amount"] == Decimal("15000.00")
    assert result["remaining_a_to_b"] == Decimal("15000.00")

    old.refresh_from_db()
    new.refresh_from_db()
    counter.refresh_from_db()
    # Старейший долг гасится первым и целиком, новый — частично.
    assert old.status == Debt.Status.CLOSED
    assert new.status == Debt.Status.OPEN
    assert services.debt_remaining(new) == Decimal("15000.00")
    assert counter.status == Debt.Status.CLOSED


def test_net_debts_nothing_to_net(accountant):
    a, b = f.BusinessFactory(), f.BusinessFactory()
    f.DebtFactory(debtor=a, creditor=b, amount=Decimal("5000.00"))  # только одна сторона
    with pytest.raises(DomainError) as exc:
        services.net_debts(accountant, business_a=a, business_b=b)
    assert exc.value.code == "nothing_to_net"
    assert exc.value.details == {"a_to_b": "5000.00", "b_to_a": "0.00"}


def test_net_debts_disabled_by_rules(accountant, monkeypatch):
    monkeypatch.setitem(services.HOLDING_RULES, "netting_mode", "off")
    a, b = f.BusinessFactory(), f.BusinessFactory()
    f.DebtFactory(debtor=a, creditor=b, amount=Decimal("1000.00"))
    f.DebtFactory(debtor=b, creditor=a, amount=Decimal("1000.00"))
    with pytest.raises(NotAllowedError) as exc:
        services.net_debts(accountant, business_a=a, business_b=b)
    assert exc.value.code == "netting_off"


def test_net_debts_same_business_rejected(accountant, business):
    with pytest.raises(DomainError) as exc:
        services.net_debts(accountant, business_a=business, business_b=business)
    assert exc.value.code == "netting_self"


# --- create_barter (БАР-04) ---
def test_create_barter_requires_finance_controller(accountant, cashier):
    a, b = f.BusinessFactory(), f.BusinessFactory()
    with pytest.raises(NotAllowedError) as exc:
        services.create_barter(
            accountant,
            business_a=a,
            business_b=b,
            description="дрова за цемент",
            value=Decimal("3000.00"),
            controlled_by=cashier,
        )
    assert exc.value.code == "barter_controller_role"
    assert Barter.objects.count() == 0


def test_create_barter_by_accountant_controller(chief, accountant):
    a, b = f.BusinessFactory(), f.BusinessFactory()
    barter = services.create_barter(
        chief,
        business_a=a,
        business_b=b,
        description="дрова за цемент",
        value=Decimal("3000.00"),
        controlled_by=accountant,
    )
    assert barter.status == Barter.Status.ACTIVE
    assert barter.controlled_by == accountant

    log = AuditLog.objects.get(action="barter.created", entity_id=str(barter.pk))
    assert log.actor == chief
    assert log.after["value"] == "3000.00"
    assert log.after["controlled_by"] == accountant.pk


# --- close_debt_with_barter (ХОЛ-33) ---
def test_barter_closes_debt_partially(accountant):
    a, b = f.BusinessFactory(), f.BusinessFactory()
    barter = f.BarterFactory(business_a=a, business_b=b, value=Decimal("3000.00"))
    debt = f.DebtFactory(debtor=a, creditor=b, amount=Decimal("5000.00"))

    settlement = services.close_debt_with_barter(
        accountant, barter_id=barter.pk, debt_id=debt.pk
    )
    # Гасится min(оценка, остаток) = 3000.
    assert settlement.amount == Decimal("3000.00")
    assert settlement.barter == barter
    assert settlement.method == DebtSettlement.Method.OFFSET

    debt.refresh_from_db()
    barter.refresh_from_db()
    assert debt.status == Debt.Status.OPEN
    assert services.debt_remaining(debt) == Decimal("2000.00")
    assert barter.status == Barter.Status.COMPLETED

    log = AuditLog.objects.get(action="barter.closed_debt", entity_id=str(barter.pk))
    assert log.after == {"debt_id": debt.pk, "amount": "3000.00"}
    assert AuditLog.objects.filter(action="debt.settled").count() == 1


def test_barter_closes_debt_fully_when_value_exceeds(accountant):
    a, b = f.BusinessFactory(), f.BusinessFactory()
    barter = f.BarterFactory(business_a=a, business_b=b, value=Decimal("9000.00"))
    # Долг может быть и в обратную сторону — стороны совпадают как множество.
    debt = f.DebtFactory(debtor=b, creditor=a, amount=Decimal("5000.00"))

    settlement = services.close_debt_with_barter(
        accountant, barter_id=barter.pk, debt_id=debt.pk
    )
    assert settlement.amount == Decimal("5000.00")
    debt.refresh_from_db()
    assert debt.status == Debt.Status.CLOSED
    assert debt.closed_at is not None


def test_barter_debt_mismatch(accountant):
    barter = f.BarterFactory()
    debt = f.DebtFactory()  # другие бизнесы
    with pytest.raises(DomainError) as exc:
        services.close_debt_with_barter(accountant, barter_id=barter.pk, debt_id=debt.pk)
    assert exc.value.code == "barter_debt_mismatch"
    assert debt.settlements.count() == 0
    barter.refresh_from_db()
    assert barter.status == Barter.Status.ACTIVE


def test_barter_close_debt_repeat_conflict(accountant):
    a, b = f.BusinessFactory(), f.BusinessFactory()
    barter = f.BarterFactory(business_a=a, business_b=b, value=Decimal("1000.00"))
    debt = f.DebtFactory(debtor=a, creditor=b, amount=Decimal("5000.00"))
    services.close_debt_with_barter(accountant, barter_id=barter.pk, debt_id=debt.pk)
    # Бартер уже completed — повторное применение конфликтует.
    with pytest.raises(ConflictError):
        services.close_debt_with_barter(accountant, barter_id=barter.pk, debt_id=debt.pk)
    assert debt.settlements.count() == 1


def test_inactive_barter_cannot_close_debt(accountant):
    a, b = f.BusinessFactory(), f.BusinessFactory()
    barter = f.BarterFactory(
        business_a=a, business_b=b, status=Barter.Status.CANCELLED
    )
    debt = f.DebtFactory(debtor=a, creditor=b)
    with pytest.raises(ConflictError):
        services.close_debt_with_barter(accountant, barter_id=barter.pk, debt_id=debt.pk)


def test_barter_close_disabled_by_rules(accountant, monkeypatch):
    monkeypatch.setitem(services.HOLDING_RULES, "barter_can_close_debt", False)
    a, b = f.BusinessFactory(), f.BusinessFactory()
    barter = f.BarterFactory(business_a=a, business_b=b)
    debt = f.DebtFactory(debtor=a, creditor=b)
    with pytest.raises(NotAllowedError) as exc:
        services.close_debt_with_barter(accountant, barter_id=barter.pk, debt_id=debt.pk)
    assert exc.value.code == "barter_close_off"


# --- complete / cancel: идемпотентность ---
def test_complete_barter_idempotency(accountant):
    barter = f.BarterFactory()
    completed = services.complete_barter(accountant, barter_id=barter.pk)
    assert completed.status == Barter.Status.COMPLETED
    log = AuditLog.objects.get(action="barter.completed", entity_id=str(barter.pk))
    assert log.before == {"status": "active"}
    assert log.after == {"status": "completed"}

    with pytest.raises(ConflictError):
        services.complete_barter(accountant, barter_id=barter.pk)
    assert AuditLog.objects.filter(action="barter.completed").count() == 1


def test_cancel_barter_idempotency(accountant):
    barter = f.BarterFactory()
    cancelled = services.cancel_barter(accountant, barter_id=barter.pk)
    assert cancelled.status == Barter.Status.CANCELLED
    log = AuditLog.objects.get(action="barter.cancelled", entity_id=str(barter.pk))
    assert log.after == {"status": "cancelled"}

    with pytest.raises(ConflictError):
        services.cancel_barter(accountant, barter_id=barter.pk)
    # Отменённый нельзя завершить.
    with pytest.raises(ConflictError):
        services.complete_barter(accountant, barter_id=barter.pk)
