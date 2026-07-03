"""Тесты передач: БАР-01/ХОЛ-30 (авто-долг при одобрении), ХОЛ-32 (порог владельца)."""
from decimal import Decimal

import pytest

from apps.audit.models import AuditLog
from apps.core.exceptions import ConflictError, DomainError, NotAllowedError
from apps.settlements import services
from apps.settlements.models import Debt, Transfer
from apps.testing import factories as f

pytestmark = pytest.mark.django_db


# --- create_transfer ---
def test_create_transfer_below_threshold(accountant):
    src, dst = f.BusinessFactory(), f.BusinessFactory()
    tr = services.create_transfer(
        accountant,
        from_business=src,
        to_business=dst,
        amount=Decimal("5000.00"),
        note="аванс",
    )
    assert tr.status == Transfer.Status.PENDING
    assert tr.requires_owner_approval is False
    assert tr.created_by == accountant
    assert tr.approved_by is None
    assert tr.note == "аванс"

    log = AuditLog.objects.get(action="transfer.created", entity_id=str(tr.pk))
    assert log.entity_type == "Transfer"
    assert log.actor == accountant
    assert log.after["amount"] == "5000.00"
    assert log.after["requires_owner_approval"] is False


def test_create_transfer_to_self_rejected(accountant, business):
    with pytest.raises(DomainError) as exc:
        services.create_transfer(
            accountant,
            from_business=business,
            to_business=business,
            amount=Decimal("100.00"),
        )
    assert exc.value.code == "transfer_self"
    assert Transfer.objects.count() == 0


def test_create_transfer_nonpositive_amount(accountant):
    src, dst = f.BusinessFactory(), f.BusinessFactory()
    with pytest.raises(DomainError) as exc:
        services.create_transfer(
            accountant, from_business=src, to_business=dst, amount=Decimal("0")
        )
    assert exc.value.code == "invalid_amount"


# --- approve_transfer: БАР-01 / ХОЛ-30 ---
def test_approve_transfer_creates_debt(accountant):
    tr = f.TransferFactory(amount=Decimal("7500.00"))
    debt = services.approve_transfer(transfer_id=tr.pk, actor=accountant)

    tr.refresh_from_db()
    assert tr.status == Transfer.Status.APPROVED
    assert tr.approved_by == accountant

    # ХОЛ-30: долг получатель → отправитель на сумму передачи.
    assert debt is not None
    assert debt.debtor == tr.to_business
    assert debt.creditor == tr.from_business
    assert debt.amount == Decimal("7500.00")
    assert debt.source_transfer == tr
    assert debt.status == Debt.Status.OPEN
    assert Debt.objects.count() == 1

    log = AuditLog.objects.get(action="transfer.approved", entity_id=str(tr.pk))
    assert log.actor == accountant
    assert log.before == {"status": "pending"}
    assert log.after == {"status": "approved", "debt_id": debt.pk}


def test_double_approve_raises_conflict(accountant, chief):
    tr = f.TransferFactory()
    services.approve_transfer(transfer_id=tr.pk, actor=accountant)
    with pytest.raises(ConflictError):
        services.approve_transfer(transfer_id=tr.pk, actor=chief)
    # Долг не задвоился, аудит одобрения — единственный.
    assert Debt.objects.filter(source_transfer=tr).count() == 1
    assert AuditLog.objects.filter(
        action="transfer.approved", entity_id=str(tr.pk)
    ).count() == 1


def test_reject_transfer(accountant):
    tr = f.TransferFactory()
    rejected = services.reject_transfer(accountant, transfer_id=tr.pk)
    assert rejected.status == Transfer.Status.REJECTED
    assert rejected.approved_by == accountant
    # Отклонение долга не создаёт.
    assert Debt.objects.count() == 0

    log = AuditLog.objects.get(action="transfer.rejected", entity_id=str(tr.pk))
    assert log.before == {"status": "pending"}
    assert log.after == {"status": "rejected"}


def test_double_reject_raises_conflict(accountant):
    tr = f.TransferFactory()
    services.reject_transfer(accountant, transfer_id=tr.pk)
    with pytest.raises(ConflictError):
        services.reject_transfer(accountant, transfer_id=tr.pk)


def test_approve_after_reject_raises_conflict(accountant):
    tr = f.TransferFactory()
    services.reject_transfer(accountant, transfer_id=tr.pk)
    with pytest.raises(ConflictError):
        services.approve_transfer(transfer_id=tr.pk, actor=accountant)
    assert Debt.objects.count() == 0


# --- ХОЛ-32: порог одобрения владельцем ---
def test_transfer_above_threshold_flagged(accountant):
    src, dst = f.BusinessFactory(), f.BusinessFactory()
    tr = services.create_transfer(
        accountant,
        from_business=src,
        to_business=dst,
        amount=Decimal("50000.01"),
    )
    assert tr.requires_owner_approval is True


def test_transfer_exactly_threshold_not_flagged(accountant):
    src, dst = f.BusinessFactory(), f.BusinessFactory()
    tr = services.create_transfer(
        accountant,
        from_business=src,
        to_business=dst,
        amount=Decimal("50000.00"),
    )
    assert tr.requires_owner_approval is False
    # Ровно порог одобряет бухгалтер без владельца.
    debt = services.approve_transfer(transfer_id=tr.pk, actor=accountant)
    tr.refresh_from_db()
    assert tr.status == Transfer.Status.APPROVED
    assert debt.amount == Decimal("50000.00")


def test_accountant_cannot_approve_above_threshold(accountant):
    src, dst = f.BusinessFactory(), f.BusinessFactory()
    tr = services.create_transfer(
        accountant,
        from_business=src,
        to_business=dst,
        amount=Decimal("60000.00"),
    )
    with pytest.raises(NotAllowedError) as exc:
        services.approve_transfer(transfer_id=tr.pk, actor=accountant)
    assert exc.value.code == "owner_approval_required"
    assert exc.value.details["threshold"] == "50000"
    assert exc.value.details["amount"] == "60000.00"

    tr.refresh_from_db()
    assert tr.status == Transfer.Status.PENDING  # не тронута
    assert Debt.objects.count() == 0


def test_owner_approves_above_threshold(accountant, owner_user):
    src, dst = f.BusinessFactory(), f.BusinessFactory()
    tr = services.create_transfer(
        accountant,
        from_business=src,
        to_business=dst,
        amount=Decimal("60000.00"),
    )
    debt = services.approve_transfer(transfer_id=tr.pk, actor=owner_user)
    tr.refresh_from_db()
    assert tr.status == Transfer.Status.APPROVED
    assert tr.approved_by == owner_user
    assert debt is not None and debt.amount == Decimal("60000.00")
