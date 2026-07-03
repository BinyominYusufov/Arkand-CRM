"""Сервисы касс: вся запись — здесь, в transaction.atomic()."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.exceptions import (
    DomainError,
    InsufficientFundsError,
    LimitExceededError,
)

from . import selectors
from .models import CashOperation, CashRegister


@transaction.atomic
def create_cash_operation(
    actor,
    *,
    register: CashRegister,
    direction: str,
    method: str,
    amount: Decimal,
    occurred_at=None,
    note: str = "",
) -> CashOperation:
    """КАС-02/03: операция кассы с проверкой лимита оборота и остатка."""
    if amount <= 0:
        raise DomainError("Сумма должна быть больше нуля", code="invalid_amount")
    if not register.is_active:
        raise DomainError("Касса не активна", code="cash_register_inactive")

    occurred_at = occurred_at or timezone.now()

    # КАС-03: лимит оборота за календарный месяц операции.
    limit = register.turnover_limit
    if limit and limit > 0:
        current = selectors.register_month_turnover(
            register, occurred_at.year, occurred_at.month
        )
        if current + amount > limit:
            raise LimitExceededError(
                "Превышен лимит оборота кассы",
                details={
                    "limit": str(limit),
                    "current_turnover": str(current),
                    "attempted": str(amount),
                },
            )

    # Расход не может превышать остаток (остаток = сумма операций, КАС-02).
    if direction == CashOperation.Direction.OUT:
        balance = selectors.register_balance(register)
        if amount > balance:
            raise InsufficientFundsError(
                "Недостаточно средств в кассе",
                details={"balance": str(balance), "attempted": str(amount)},
            )

    op = CashOperation.objects.create(
        register=register,
        direction=direction,
        method=method,
        amount=amount,
        note=note,
        created_by=actor,
        occurred_at=occurred_at,
    )
    AuditLog.record(
        actor,
        "cash_operation.created",
        op,
        after={
            "register_id": register.id,
            "direction": direction,
            "method": method,
            "amount": str(amount),
            "occurred_at": occurred_at.isoformat(),
        },
    )
    return op


@transaction.atomic
def soft_delete_cash_operation(actor, *, operation_id: int) -> CashOperation:
    from apps.core.exceptions import ConflictError

    updated = CashOperation.objects.filter(id=operation_id, is_deleted=False).update(
        is_deleted=True, updated_at=timezone.now()
    )
    if updated == 0:
        raise ConflictError("Операция уже удалена или не найдена")
    op = CashOperation.objects.get(id=operation_id)
    AuditLog.record(
        actor,
        "cash_operation.soft_deleted",
        op,
        before={"is_deleted": False},
        after={"is_deleted": True},
    )
    return op
