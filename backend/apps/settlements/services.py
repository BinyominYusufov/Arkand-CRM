"""Сервисы взаиморасчётов (БАР-01…04, ХОЛ-30…33).

Правила холдинга читаются ТОЛЬКО из holding_rules.HOLDING_RULES.
Идемпотентность — условный UPDATE по статусу (SQLite, без блокировок).
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.exceptions import ConflictError, DomainError, NotAllowedError
from apps.core.models import Business

from .holding_rules import HOLDING_RULES
from .models import Barter, Debt, DebtSettlement, Transfer

ZERO = Decimal("0.00")


def _debt_settled_amount(debt: Debt) -> Decimal:
    from django.db.models import Sum

    return debt.settlements.aggregate(s=Sum("amount"))["s"] or ZERO


def debt_remaining(debt: Debt) -> Decimal:
    return debt.amount - _debt_settled_amount(debt)


# --- Передачи ---
@transaction.atomic
def create_transfer(
    actor, *, from_business: Business, to_business: Business, amount: Decimal, note: str = ""
) -> Transfer:
    if from_business.pk == to_business.pk:
        raise DomainError("Нельзя передавать самому себе", code="transfer_self")
    if amount <= 0:
        raise DomainError("Сумма должна быть больше нуля", code="invalid_amount")

    # ХОЛ-32: сверх порога — одобрение только владельцем.
    threshold = HOLDING_RULES["owner_approval_threshold"]
    requires_owner = bool(threshold and threshold > 0 and amount > threshold)

    tr = Transfer.objects.create(
        from_business=from_business,
        to_business=to_business,
        amount=amount,
        note=note,
        created_by=actor,
        requires_owner_approval=requires_owner,
    )
    AuditLog.record(
        actor,
        "transfer.created",
        tr,
        after={
            "from": from_business.pk,
            "to": to_business.pk,
            "amount": str(amount),
            "requires_owner_approval": requires_owner,
        },
    )
    return tr


@transaction.atomic
def approve_transfer(*, transfer_id: int, actor) -> Debt | None:
    """БАР-01/ХОЛ-30: одобрение передачи с автофиксацией долга.

    Защита от двойного одобрения — условный UPDATE по статусу:
    повторный вызов получает rowcount 0 и ConflictError.
    """
    pending = Transfer.objects.filter(id=transfer_id, status=Transfer.Status.PENDING)
    tr_check = pending.first()
    if tr_check is None:
        raise ConflictError("Передача уже обработана")
    # ХОЛ-32: сверх порога одобряет только владелец.
    if tr_check.requires_owner_approval and not (
        actor.is_owner_role or actor.is_superuser
    ):
        raise NotAllowedError(
            "Передача сверх порога — требуется одобрение владельца",
            code="owner_approval_required",
            details={
                "threshold": str(HOLDING_RULES["owner_approval_threshold"]),
                "amount": str(tr_check.amount),
            },
        )

    updated = pending.update(
        status=Transfer.Status.APPROVED, approved_by=actor, updated_at=timezone.now()
    )
    if updated == 0:
        raise ConflictError("Передача уже обработана")

    transfer = Transfer.objects.get(id=transfer_id)
    debt = None
    if HOLDING_RULES["auto_debt_on_transfer"]:  # ХОЛ-30
        debt = Debt.objects.create(
            debtor=transfer.to_business,
            creditor=transfer.from_business,
            amount=transfer.amount,
            source_transfer=transfer,
            status=Debt.Status.OPEN,
        )
    AuditLog.record(
        actor,
        "transfer.approved",
        transfer,
        before={"status": Transfer.Status.PENDING},
        after={"status": transfer.status, "debt_id": debt.pk if debt else None},
    )
    return debt


@transaction.atomic
def reject_transfer(actor, *, transfer_id: int) -> Transfer:
    updated = Transfer.objects.filter(
        id=transfer_id, status=Transfer.Status.PENDING
    ).update(status=Transfer.Status.REJECTED, approved_by=actor, updated_at=timezone.now())
    if updated == 0:
        raise ConflictError("Передача уже обработана")
    transfer = Transfer.objects.get(id=transfer_id)
    AuditLog.record(
        actor,
        "transfer.rejected",
        transfer,
        before={"status": Transfer.Status.PENDING},
        after={"status": transfer.status},
    )
    return transfer


# --- Долги ---
@transaction.atomic
def settle_debt(
    actor,
    *,
    debt_id: int,
    method: str,
    amount: Decimal | None = None,
    note: str = "",
    barter: Barter | None = None,
) -> DebtSettlement:
    """БАР-03: погашение долга взаимозачётом или возвратом (можно частично)."""
    try:
        debt = Debt.objects.get(id=debt_id)
    except Debt.DoesNotExist:
        raise ConflictError("Долг не найден")
    if debt.status != Debt.Status.OPEN:
        raise ConflictError("Долг уже закрыт")

    remaining = debt_remaining(debt)
    if amount is None:
        amount = remaining
    if amount <= 0:
        raise DomainError("Сумма должна быть больше нуля", code="invalid_amount")
    if amount > remaining:
        raise DomainError(
            "Сумма погашения превышает остаток долга",
            code="settlement_exceeds_debt",
            details={"remaining": str(remaining), "attempted": str(amount)},
        )

    settlement = DebtSettlement.objects.create(
        debt=debt,
        method=method,
        amount=amount,
        note=note,
        barter=barter,
        created_by=actor,
    )
    new_remaining = remaining - amount
    if new_remaining == ZERO:
        # Условный UPDATE по статусу — защита от гонки двойного закрытия.
        updated = Debt.objects.filter(id=debt.pk, status=Debt.Status.OPEN).update(
            status=Debt.Status.CLOSED, closed_at=timezone.now()
        )
        if updated == 0:
            raise ConflictError("Долг уже закрыт")
    AuditLog.record(
        actor,
        "debt.settled",
        debt,
        before={"remaining": str(remaining), "status": Debt.Status.OPEN},
        after={
            "remaining": str(new_remaining),
            "status": Debt.Status.CLOSED if new_remaining == ZERO else Debt.Status.OPEN,
            "method": method,
            "amount": str(amount),
            "barter_id": barter.pk if barter else None,
        },
    )
    return settlement


@transaction.atomic
def net_debts(actor, *, business_a: Business, business_b: Business) -> dict:
    """ХОЛ-31: двусторонний неттинг — встречные долги гасятся до меньшей суммы.

    # TODO: заменить на реальные правила ХОЛ-31, когда появятся.
    """
    if HOLDING_RULES["netting_mode"] != "bilateral":
        raise NotAllowedError("Взаимозачёт отключён правилами холдинга", code="netting_off")
    if business_a.pk == business_b.pk:
        raise DomainError("Неттинг требует два разных бизнеса", code="netting_self")

    debts_ab = list(
        Debt.objects.filter(
            debtor=business_a, creditor=business_b, status=Debt.Status.OPEN
        ).order_by("created_at")
    )
    debts_ba = list(
        Debt.objects.filter(
            debtor=business_b, creditor=business_a, status=Debt.Status.OPEN
        ).order_by("created_at")
    )
    total_ab = sum((debt_remaining(d) for d in debts_ab), ZERO)
    total_ba = sum((debt_remaining(d) for d in debts_ba), ZERO)
    net_amount = min(total_ab, total_ba)
    if net_amount <= 0:
        raise DomainError(
            "Нет встречных долгов для взаимозачёта",
            code="nothing_to_net",
            details={"a_to_b": str(total_ab), "b_to_a": str(total_ba)},
        )

    def _apply(debts: list[Debt], to_offset: Decimal) -> None:
        # Гасим по очереди, начиная со старейших долгов.
        for d in debts:
            if to_offset <= 0:
                break
            portion = min(debt_remaining(d), to_offset)
            if portion <= 0:
                continue
            settle_debt(
                actor,
                debt_id=d.pk,
                method=DebtSettlement.Method.OFFSET,
                amount=portion,
                note="Взаимозачёт (ХОЛ-31)",
            )
            to_offset -= portion

    _apply(debts_ab, net_amount)
    _apply(debts_ba, net_amount)

    result = {
        "business_a": business_a.pk,
        "business_b": business_b.pk,
        "netted_amount": net_amount,
        "remaining_a_to_b": total_ab - net_amount,
        "remaining_b_to_a": total_ba - net_amount,
    }
    # Аудит на уровне пары бизнесов: привязываем к бизнесу-инициатору.
    AuditLog.record(
        actor,
        "debts.netted",
        business_a,
        after={k: str(v) for k, v in result.items()},
    )
    return result


# --- Бартер ---
@transaction.atomic
def create_barter(
    actor,
    *,
    business_a: Business,
    business_b: Business,
    description: str,
    value: Decimal,
    controlled_by,
) -> Barter:
    """БАР-04: бартер между своими, под контролем бухгалтера."""
    if business_a.pk == business_b.pk:
        raise DomainError("Бартер требует два разных бизнеса", code="barter_self")
    if value <= 0:
        raise DomainError("Оценка должна быть больше нуля", code="invalid_amount")
    if not controlled_by.is_finance:
        raise NotAllowedError(
            "Контролировать бартер может только бухгалтер", code="barter_controller_role"
        )
    barter = Barter.objects.create(
        business_a=business_a,
        business_b=business_b,
        description=description,
        value=value,
        controlled_by=controlled_by,
    )
    AuditLog.record(
        actor,
        "barter.created",
        barter,
        after={
            "business_a": business_a.pk,
            "business_b": business_b.pk,
            "value": str(value),
            "controlled_by": controlled_by.pk,
        },
    )
    return barter


@transaction.atomic
def close_debt_with_barter(actor, *, barter_id: int, debt_id: int) -> DebtSettlement:
    """ХОЛ-33: бартер закрывает встречный долг на сумму оценки.

    # TODO: заменить на реальные правила ХОЛ-33, когда появятся.
    """
    if not HOLDING_RULES["barter_can_close_debt"]:
        raise NotAllowedError(
            "Закрытие долга бартером отключено правилами холдинга",
            code="barter_close_off",
        )
    try:
        barter = Barter.objects.get(id=barter_id)
    except Barter.DoesNotExist:
        raise ConflictError("Бартер не найден")
    if barter.status != Barter.Status.ACTIVE:
        raise ConflictError("Бартер уже завершён или отменён")
    try:
        debt = Debt.objects.get(id=debt_id)
    except Debt.DoesNotExist:
        raise ConflictError("Долг не найден")

    pair = {barter.business_a_id, barter.business_b_id}
    if {debt.debtor_id, debt.creditor_id} != pair:
        raise DomainError(
            "Долг не между сторонами бартера", code="barter_debt_mismatch"
        )

    amount = min(barter.value, debt_remaining(debt))
    settlement = settle_debt(
        actor,
        debt_id=debt.pk,
        method=DebtSettlement.Method.OFFSET,
        amount=amount,
        note=f"Закрыто бартером #{barter.pk} (ХОЛ-33)",
        barter=barter,
    )
    # Бартер, применённый к долгу, считаем завершённым.
    Barter.objects.filter(id=barter.pk, status=Barter.Status.ACTIVE).update(
        status=Barter.Status.COMPLETED, updated_at=timezone.now()
    )
    AuditLog.record(
        actor,
        "barter.closed_debt",
        barter,
        after={"debt_id": debt.pk, "amount": str(amount)},
    )
    return settlement


@transaction.atomic
def complete_barter(actor, *, barter_id: int) -> Barter:
    updated = Barter.objects.filter(id=barter_id, status=Barter.Status.ACTIVE).update(
        status=Barter.Status.COMPLETED, updated_at=timezone.now()
    )
    if updated == 0:
        raise ConflictError("Бартер уже обработан")
    barter = Barter.objects.get(id=barter_id)
    AuditLog.record(
        actor,
        "barter.completed",
        barter,
        before={"status": Barter.Status.ACTIVE},
        after={"status": barter.status},
    )
    return barter


@transaction.atomic
def cancel_barter(actor, *, barter_id: int) -> Barter:
    updated = Barter.objects.filter(id=barter_id, status=Barter.Status.ACTIVE).update(
        status=Barter.Status.CANCELLED, updated_at=timezone.now()
    )
    if updated == 0:
        raise ConflictError("Бартер уже обработан")
    barter = Barter.objects.get(id=barter_id)
    AuditLog.record(
        actor,
        "barter.cancelled",
        barter,
        before={"status": Barter.Status.ACTIVE},
        after={"status": barter.status},
    )
    return barter
