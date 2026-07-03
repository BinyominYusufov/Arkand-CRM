"""Сервисы финансов — единственное место записи в БД (ТЗ, раздел 3).

Все денежные операции в transaction.atomic(); идемпотентность — через
условный UPDATE по статусу (SQLite: не полагаемся на select_for_update).
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.exceptions import ConflictError, DomainError
from apps.core.models import Business

from .models import ExpenseCategory, Transaction


def _tx_snapshot(tx: Transaction) -> dict:
    return {
        "business_id": tx.business_id,
        "kind": tx.kind,
        "category_id": tx.category_id,
        "amount": str(tx.amount),
        "method": tx.method,
        "status": tx.status,
        "occurred_at": tx.occurred_at.isoformat(),
    }


@transaction.atomic
def create_income(
    actor,
    *,
    business: Business,
    amount: Decimal,
    method: str,
    occurred_at=None,
    note: str = "",
) -> Transaction:
    """ФНС-01: приход создаётся в статусе pending и ждёт подтверждения."""
    if amount <= 0:
        raise DomainError("Сумма должна быть больше нуля", code="invalid_amount")
    tx = Transaction.objects.create(
        business=business,
        kind=Transaction.Kind.INCOME,
        category=None,
        amount=amount,
        method=method,
        status=Transaction.Status.PENDING,
        occurred_at=occurred_at or timezone.now(),
        note=note,
        created_by=actor,
    )
    AuditLog.record(actor, "transaction.income_created", tx, after=_tx_snapshot(tx))
    return tx


@transaction.atomic
def create_expense(
    actor,
    *,
    business: Business,
    category: ExpenseCategory,
    amount: Decimal,
    method: str,
    occurred_at=None,
    note: str = "",
) -> Transaction:
    """ФНС-02/03: расход по категории; фиксируется сразу (создаёт финотдел)."""
    if amount <= 0:
        raise DomainError("Сумма должна быть больше нуля", code="invalid_amount")
    if category is None:
        raise DomainError("Для расхода обязательна категория", code="category_required")
    tx = Transaction.objects.create(
        business=business,
        kind=Transaction.Kind.EXPENSE,
        category=category,
        amount=amount,
        method=method,
        status=Transaction.Status.CONFIRMED,
        confirmed_by=actor,
        occurred_at=occurred_at or timezone.now(),
        note=note,
        created_by=actor,
    )
    AuditLog.record(actor, "transaction.expense_created", tx, after=_tx_snapshot(tx))
    return tx


@transaction.atomic
def confirm_income(actor, *, transaction_id: int) -> Transaction:
    """ФНС-01: подтверждение прихода финансистом.

    Идемпотентность: условный UPDATE по статусу — повторное подтверждение
    (или гонка) получает rowcount 0 и ConflictError, без блокировок.
    """
    updated = Transaction.objects.filter(
        id=transaction_id,
        kind=Transaction.Kind.INCOME,
        status=Transaction.Status.PENDING,
        is_deleted=False,
    ).update(
        status=Transaction.Status.CONFIRMED,
        confirmed_by=actor,
        updated_at=timezone.now(),
    )
    if updated == 0:
        raise ConflictError("Приход уже обработан или не найден")
    tx = Transaction.objects.get(id=transaction_id)
    AuditLog.record(
        actor,
        "transaction.income_confirmed",
        tx,
        before={"status": Transaction.Status.PENDING},
        after={"status": tx.status, "confirmed_by_id": actor.pk},
    )
    return tx


@transaction.atomic
def void_transaction(actor, *, transaction_id: int) -> Transaction:
    """Аннулирование операции (вместо удаления денег)."""
    updated = Transaction.objects.filter(
        id=transaction_id,
        status__in=[Transaction.Status.PENDING, Transaction.Status.CONFIRMED],
        is_deleted=False,
    ).update(status=Transaction.Status.VOID, updated_at=timezone.now())
    if updated == 0:
        raise ConflictError("Операция уже аннулирована или не найдена")
    tx = Transaction.objects.get(id=transaction_id)
    AuditLog.record(
        actor,
        "transaction.voided",
        tx,
        before={"status": "pending|confirmed"},
        after={"status": tx.status},
    )
    return tx


@transaction.atomic
def soft_delete_transaction(actor, *, transaction_id: int) -> Transaction:
    """Soft-delete: финансовые записи физически не удаляются (ТЗ, раздел 11)."""
    updated = Transaction.objects.filter(id=transaction_id, is_deleted=False).update(
        is_deleted=True, updated_at=timezone.now()
    )
    if updated == 0:
        raise ConflictError("Операция уже удалена или не найдена")
    tx = Transaction.objects.get(id=transaction_id)
    AuditLog.record(
        actor,
        "transaction.soft_deleted",
        tx,
        before={"is_deleted": False},
        after={"is_deleted": True},
    )
    return tx
