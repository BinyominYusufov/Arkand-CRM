"""Тесты сервисов и селекторов касс (КАС-02, КАС-03)."""
from datetime import datetime, timezone as dt_tz
from decimal import Decimal

import pytest

from apps.audit.models import AuditLog
from apps.cash import selectors, services
from apps.cash.models import CashOperation
from apps.core.exceptions import (
    ConflictError,
    DomainError,
    InsufficientFundsError,
    LimitExceededError,
)
from apps.testing import factories as f

pytestmark = pytest.mark.django_db

# Середина месяца в UTC: и в UTC, и в Asia/Dushanbe (+5) это один и тот же месяц.
MAY = datetime(2026, 5, 15, 10, 0, tzinfo=dt_tz.utc)
APRIL = datetime(2026, 4, 15, 10, 0, tzinfo=dt_tz.utc)


def _register(limit="50000.00"):
    return f.CashRegisterFactory(turnover_limit=Decimal(limit))


def _op(register, direction, amount, occurred_at=MAY, **kwargs):
    return f.CashOperationFactory(
        register=register,
        direction=direction,
        amount=Decimal(amount),
        occurred_at=occurred_at,
        **kwargs,
    )


# ---------- КАС-03: лимит оборота ----------


def test_month_turnover_counts_in_plus_out(accountant):
    reg = _register()
    _op(reg, CashOperation.Direction.IN, "30000.00")
    _op(reg, CashOperation.Direction.OUT, "10000.00")

    assert selectors.register_month_turnover(reg, 2026, 5) == Decimal("40000.00")


def test_operation_exactly_reaching_limit_passes(accountant):
    reg = _register("50000.00")
    _op(reg, CashOperation.Direction.IN, "30000.00")
    _op(reg, CashOperation.Direction.OUT, "10000.00")  # оборот 40000

    op = services.create_cash_operation(
        accountant,
        register=reg,
        direction=CashOperation.Direction.IN,
        method=CashOperation.Method.CASH,
        amount=Decimal("10000.00"),  # ровно до лимита 50000
        occurred_at=MAY,
    )
    assert op.pk is not None
    assert selectors.register_month_turnover(reg, 2026, 5) == Decimal("50000.00")


def test_operation_over_limit_raises_with_details(accountant):
    reg = _register("50000.00")
    _op(reg, CashOperation.Direction.IN, "30000.00")
    _op(reg, CashOperation.Direction.OUT, "10000.00")

    with pytest.raises(LimitExceededError) as exc:
        services.create_cash_operation(
            accountant,
            register=reg,
            direction=CashOperation.Direction.IN,
            method=CashOperation.Method.CASH,
            amount=Decimal("10000.01"),
            occurred_at=MAY,
        )
    err = exc.value
    assert err.code == "cash_limit_exceeded"
    assert set(err.details) == {"limit", "current_turnover", "attempted"}
    assert err.details["limit"] == "50000.00"
    assert err.details["attempted"] == "10000.01"
    # Сравниваем как Decimal: на SQLite Sum() теряет масштаб ("40000" vs "40000.00").
    assert Decimal(err.details["current_turnover"]) == Decimal("40000.00")
    # Операция не должна быть записана.
    assert reg.operations.count() == 2


def test_limit_is_per_month_of_occurred_at(accountant):
    """Оборот другого месяца не влияет на лимит текущего."""
    reg = _register("50000.00")
    _op(reg, CashOperation.Direction.IN, "45000.00", occurred_at=APRIL)

    # В мае оборот пуст — операция на весь лимит проходит.
    op = services.create_cash_operation(
        accountant,
        register=reg,
        direction=CashOperation.Direction.IN,
        method=CashOperation.Method.CASH,
        amount=Decimal("50000.00"),
        occurred_at=MAY,
    )
    assert op.pk is not None
    assert selectors.register_month_turnover(reg, 2026, 4) == Decimal("45000.00")
    assert selectors.register_month_turnover(reg, 2026, 5) == Decimal("50000.00")


def test_zero_limit_disables_check(accountant):
    reg = _register("0.00")
    op = services.create_cash_operation(
        accountant,
        register=reg,
        direction=CashOperation.Direction.IN,
        method=CashOperation.Method.CASH,
        amount=Decimal("999999.00"),
        occurred_at=MAY,
    )
    assert op.pk is not None


# ---------- Остаток и прочие доменные правила ----------


def test_out_over_balance_raises_insufficient_funds(accountant):
    reg = _register()
    _op(reg, CashOperation.Direction.IN, "1000.00")
    _op(reg, CashOperation.Direction.OUT, "400.00")  # остаток 600

    with pytest.raises(InsufficientFundsError) as exc:
        services.create_cash_operation(
            accountant,
            register=reg,
            direction=CashOperation.Direction.OUT,
            method=CashOperation.Method.CASH,
            amount=Decimal("600.01"),
            occurred_at=MAY,
        )
    assert exc.value.code == "insufficient_funds"
    assert set(exc.value.details) == {"balance", "attempted"}
    assert exc.value.details["attempted"] == "600.01"
    assert Decimal(exc.value.details["balance"]) == Decimal("600.00")


def test_operation_on_inactive_register_raises_domain_error(accountant):
    reg = f.CashRegisterFactory(is_active=False)
    with pytest.raises(DomainError) as exc:
        services.create_cash_operation(
            accountant,
            register=reg,
            direction=CashOperation.Direction.IN,
            method=CashOperation.Method.CASH,
            amount=Decimal("100.00"),
        )
    assert exc.value.code == "cash_register_inactive"


def test_non_positive_amount_raises_domain_error(accountant):
    reg = _register()
    with pytest.raises(DomainError) as exc:
        services.create_cash_operation(
            accountant,
            register=reg,
            direction=CashOperation.Direction.IN,
            method=CashOperation.Method.CASH,
            amount=Decimal("0.00"),
        )
    assert exc.value.code == "invalid_amount"


def test_register_balance_in_minus_out_and_ignores_soft_deleted(accountant):
    reg = _register()
    _op(reg, CashOperation.Direction.IN, "1000.00")
    _op(reg, CashOperation.Direction.OUT, "300.00")
    _op(reg, CashOperation.Direction.IN, "500.00", is_deleted=True)  # не считается

    assert selectors.register_balance(reg) == Decimal("700.00")


def test_month_turnover_ignores_soft_deleted(accountant):
    reg = _register()
    _op(reg, CashOperation.Direction.IN, "1000.00")
    _op(reg, CashOperation.Direction.OUT, "300.00")
    _op(reg, CashOperation.Direction.IN, "9999.00", is_deleted=True)

    assert selectors.register_month_turnover(reg, 2026, 5) == Decimal("1300.00")


def test_empty_register_balance_is_zero(accountant):
    reg = _register()
    assert selectors.register_balance(reg) == Decimal("0.00")
    assert selectors.register_month_turnover(reg, 2026, 5) == Decimal("0.00")


# ---------- Аудит и soft delete ----------


def test_create_operation_writes_audit_log(accountant):
    reg = _register()
    op = services.create_cash_operation(
        accountant,
        register=reg,
        direction=CashOperation.Direction.IN,
        method=CashOperation.Method.CASH,
        amount=Decimal("250.50"),
        occurred_at=MAY,
        note="выручка",
    )
    log = AuditLog.objects.get(
        action="cash_operation.created",
        entity_type="CashOperation",
        entity_id=str(op.pk),
    )
    assert log.actor == accountant
    assert log.after["register_id"] == reg.id
    assert log.after["direction"] == "in"
    assert log.after["method"] == "cash"
    assert log.after["amount"] == "250.50"
    assert op.created_by == accountant
    assert op.note == "выручка"


def test_soft_delete_marks_deleted_and_writes_audit(accountant):
    reg = _register()
    op = _op(reg, CashOperation.Direction.IN, "100.00")

    result = services.soft_delete_cash_operation(accountant, operation_id=op.id)

    assert result.is_deleted is True
    op.refresh_from_db()
    assert op.is_deleted is True
    log = AuditLog.objects.get(
        action="cash_operation.soft_deleted",
        entity_type="CashOperation",
        entity_id=str(op.pk),
    )
    assert log.actor == accountant
    assert log.before == {"is_deleted": False}
    assert log.after == {"is_deleted": True}


def test_soft_delete_is_idempotent_second_call_conflict(accountant):
    reg = _register()
    op = _op(reg, CashOperation.Direction.IN, "100.00")
    services.soft_delete_cash_operation(accountant, operation_id=op.id)

    with pytest.raises(ConflictError):
        services.soft_delete_cash_operation(accountant, operation_id=op.id)
