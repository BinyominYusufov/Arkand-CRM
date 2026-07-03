"""Тесты сервисов финансов (ФНС-01…03): статусы, идемпотентность, аудит."""
from decimal import Decimal

import pytest

from apps.audit.models import AuditLog
from apps.core.exceptions import ConflictError, DomainError
from apps.finance import selectors, services
from apps.finance.models import Transaction
from apps.testing import factories as f

pytestmark = pytest.mark.django_db


def _audit(action: str):
    return AuditLog.objects.filter(action=action)


# ---------- create_income (ФНС-01) ----------


def test_create_income_creates_pending(accountant, business):
    tx = services.create_income(
        accountant,
        business=business,
        amount=Decimal("1500.50"),
        method=Transaction.Method.CASH,
        note="аванс",
    )
    tx.refresh_from_db()
    assert tx.kind == Transaction.Kind.INCOME
    assert tx.status == Transaction.Status.PENDING
    assert tx.amount == Decimal("1500.50")
    assert tx.category is None
    assert tx.created_by == accountant
    assert tx.confirmed_by is None
    assert tx.is_deleted is False
    assert tx.note == "аванс"

    log = _audit("transaction.income_created").get()
    assert log.entity_type == "Transaction"
    assert log.entity_id == str(tx.id)
    assert log.actor == accountant
    assert log.after["amount"] == "1500.50"
    assert log.after["status"] == Transaction.Status.PENDING


@pytest.mark.parametrize("bad_amount", [Decimal("0"), Decimal("-10.00")])
def test_create_income_rejects_non_positive_amount(accountant, business, bad_amount):
    with pytest.raises(DomainError) as exc:
        services.create_income(
            accountant,
            business=business,
            amount=bad_amount,
            method=Transaction.Method.CASH,
        )
    assert exc.value.code == "invalid_amount"
    assert Transaction.objects.count() == 0
    assert AuditLog.objects.count() == 0


# ---------- confirm_income (ФНС-01) ----------


def test_confirm_income_sets_confirmed_and_confirmed_by(accountant, chief, business):
    tx = services.create_income(
        accountant, business=business, amount=Decimal("200.00"), method="cash"
    )
    confirmed = services.confirm_income(chief, transaction_id=tx.id)
    assert confirmed.id == tx.id
    assert confirmed.status == Transaction.Status.CONFIRMED
    assert confirmed.confirmed_by == chief

    log = _audit("transaction.income_confirmed").get()
    assert log.entity_id == str(tx.id)
    assert log.actor == chief
    assert log.before == {"status": Transaction.Status.PENDING}
    assert log.after["status"] == Transaction.Status.CONFIRMED
    assert log.after["confirmed_by_id"] == chief.pk


def test_confirm_income_twice_raises_conflict(accountant, chief, business):
    tx = services.create_income(
        accountant, business=business, amount=Decimal("200.00"), method="cash"
    )
    services.confirm_income(chief, transaction_id=tx.id)
    with pytest.raises(ConflictError):
        services.confirm_income(chief, transaction_id=tx.id)
    # Аудит подтверждения записан ровно один раз.
    assert _audit("transaction.income_confirmed").count() == 1
    tx.refresh_from_db()
    assert tx.confirmed_by == chief  # не перезаписано повторным вызовом


def test_confirm_expense_raises_conflict(accountant, chief, business, category):
    tx = services.create_expense(
        accountant,
        business=business,
        category=category,
        amount=Decimal("300.00"),
        method="cash",
    )
    with pytest.raises(ConflictError):
        services.confirm_income(chief, transaction_id=tx.id)


def test_confirm_void_income_raises_conflict(accountant, chief, business):
    tx = services.create_income(
        accountant, business=business, amount=Decimal("50.00"), method="cash"
    )
    services.void_transaction(accountant, transaction_id=tx.id)
    with pytest.raises(ConflictError):
        services.confirm_income(chief, transaction_id=tx.id)
    tx.refresh_from_db()
    assert tx.status == Transaction.Status.VOID


def test_confirm_missing_transaction_raises_conflict(chief):
    with pytest.raises(ConflictError):
        services.confirm_income(chief, transaction_id=999999)


# ---------- create_expense (ФНС-02/03) ----------


def test_create_expense_confirmed_immediately(accountant, business, category):
    tx = services.create_expense(
        accountant,
        business=business,
        category=category,
        amount=Decimal("999.99"),
        method=Transaction.Method.TRANSFER,
    )
    tx.refresh_from_db()
    assert tx.kind == Transaction.Kind.EXPENSE
    assert tx.status == Transaction.Status.CONFIRMED
    assert tx.category == category
    assert tx.confirmed_by == accountant
    assert tx.created_by == accountant
    assert tx.amount == Decimal("999.99")

    log = _audit("transaction.expense_created").get()
    assert log.entity_type == "Transaction"
    assert log.entity_id == str(tx.id)
    assert log.after["category_id"] == category.id
    assert log.after["status"] == Transaction.Status.CONFIRMED


def test_create_expense_requires_category(accountant, business):
    with pytest.raises(DomainError) as exc:
        services.create_expense(
            accountant,
            business=business,
            category=None,
            amount=Decimal("10.00"),
            method="cash",
        )
    assert exc.value.code == "category_required"
    assert Transaction.objects.count() == 0


@pytest.mark.parametrize("bad_amount", [Decimal("0.00"), Decimal("-1")])
def test_create_expense_rejects_non_positive_amount(
    accountant, business, category, bad_amount
):
    with pytest.raises(DomainError) as exc:
        services.create_expense(
            accountant,
            business=business,
            category=category,
            amount=bad_amount,
            method="cash",
        )
    assert exc.value.code == "invalid_amount"
    assert Transaction.objects.count() == 0


# ---------- void_transaction ----------


def test_void_pending_and_confirmed(accountant, chief, business, category):
    pending = services.create_income(
        accountant, business=business, amount=Decimal("100.00"), method="cash"
    )
    confirmed = services.create_expense(
        accountant,
        business=business,
        category=category,
        amount=Decimal("70.00"),
        method="cash",
    )
    for tx in (pending, confirmed):
        voided = services.void_transaction(chief, transaction_id=tx.id)
        assert voided.status == Transaction.Status.VOID

    logs = _audit("transaction.voided")
    assert logs.count() == 2
    assert {log.entity_id for log in logs} == {str(pending.id), str(confirmed.id)}


def test_void_twice_raises_conflict(accountant, business):
    tx = services.create_income(
        accountant, business=business, amount=Decimal("100.00"), method="cash"
    )
    services.void_transaction(accountant, transaction_id=tx.id)
    with pytest.raises(ConflictError):
        services.void_transaction(accountant, transaction_id=tx.id)
    assert _audit("transaction.voided").count() == 1


def test_void_missing_transaction_raises_conflict(accountant):
    with pytest.raises(ConflictError):
        services.void_transaction(accountant, transaction_id=424242)


# ---------- soft_delete_transaction ----------


def test_soft_delete_keeps_row_but_hides_from_selectors(accountant, business):
    tx = services.create_income(
        accountant, business=business, amount=Decimal("500.00"), method="cash"
    )
    deleted = services.soft_delete_transaction(accountant, transaction_id=tx.id)
    assert deleted.is_deleted is True
    # Запись физически осталась в БД.
    assert Transaction.objects.filter(id=tx.id).exists()
    assert Transaction.objects.get(id=tx.id).is_deleted is True
    # Но не видна через alive() и селектор.
    assert not Transaction.objects.alive().filter(id=tx.id).exists()
    assert tx.id not in selectors.transactions_for_user(accountant).values_list(
        "id", flat=True
    )

    log = _audit("transaction.soft_deleted").get()
    assert log.entity_id == str(tx.id)
    assert log.before == {"is_deleted": False}
    assert log.after == {"is_deleted": True}


def test_soft_delete_twice_raises_conflict(accountant, business):
    tx = services.create_income(
        accountant, business=business, amount=Decimal("500.00"), method="cash"
    )
    services.soft_delete_transaction(accountant, transaction_id=tx.id)
    with pytest.raises(ConflictError):
        services.soft_delete_transaction(accountant, transaction_id=tx.id)
    assert _audit("transaction.soft_deleted").count() == 1


def test_soft_deleted_income_cannot_be_confirmed(accountant, chief, business):
    tx = services.create_income(
        accountant, business=business, amount=Decimal("10.00"), method="cash"
    )
    services.soft_delete_transaction(accountant, transaction_id=tx.id)
    with pytest.raises(ConflictError):
        services.confirm_income(chief, transaction_id=tx.id)


def test_each_service_writes_single_audit_row(accountant, chief, business, category):
    income = services.create_income(
        accountant, business=business, amount=Decimal("1.00"), method="cash"
    )
    services.confirm_income(chief, transaction_id=income.id)
    expense = services.create_expense(
        accountant,
        business=business,
        category=category,
        amount=Decimal("2.00"),
        method="cash",
    )
    services.void_transaction(chief, transaction_id=expense.id)
    services.soft_delete_transaction(chief, transaction_id=expense.id)

    actions = list(AuditLog.objects.order_by("id").values_list("action", flat=True))
    assert actions == [
        "transaction.income_created",
        "transaction.income_confirmed",
        "transaction.expense_created",
        "transaction.voided",
        "transaction.soft_deleted",
    ]
