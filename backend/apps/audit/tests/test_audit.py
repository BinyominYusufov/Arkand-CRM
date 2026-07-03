"""Аудит: AuditLog.record, записи из денежных сервисов, API и фильтры."""
from decimal import Decimal

import pytest

from apps.audit.models import AuditLog
from apps.core.exceptions import ConflictError
from apps.finance.models import Transaction
from apps.finance.services import confirm_income, create_income
from apps.testing import factories as f

pytestmark = pytest.mark.django_db

D = Decimal


# --- AuditLog.record ---


def test_record_writes_actor_action_entity(accountant, business):
    log = AuditLog.record(
        accountant,
        "business.created",
        business,
        before=None,
        after={"name": business.name},
    )
    saved = AuditLog.objects.get(pk=log.pk)
    assert saved.actor == accountant
    assert saved.action == "business.created"
    assert saved.entity_type == "Business"
    assert saved.entity_id == str(business.pk)
    assert saved.before is None
    assert saved.after == {"name": business.name}
    assert saved.created_at is not None


def test_record_without_actor_stores_null(business):
    log = AuditLog.record(None, "system.event", business)
    assert log.actor is None
    assert log.entity_id == str(business.pk)


# --- Денежные сервисы пишут аудит ---


def test_create_income_leaves_audit_entry(accountant, business):
    tx = create_income(
        accountant, business=business, amount=D("1500.00"), method="cash"
    )
    log = AuditLog.objects.get(action="transaction.income_created")
    assert log.actor == accountant
    assert log.entity_type == "Transaction"
    assert log.entity_id == str(tx.pk)
    assert log.after["amount"] == "1500.00"
    assert log.after["status"] == Transaction.Status.PENDING
    assert log.after["business_id"] == business.id


def test_confirm_income_audited_and_idempotent(accountant, chief, business):
    tx = create_income(
        accountant, business=business, amount=D("900.00"), method="transfer"
    )
    confirm_income(chief, transaction_id=tx.id)

    logs = AuditLog.objects.filter(
        action="transaction.income_confirmed", entity_id=str(tx.id)
    )
    assert logs.count() == 1
    log = logs.get()
    assert log.actor == chief
    assert log.before == {"status": "pending"}
    assert log.after["status"] == Transaction.Status.CONFIRMED

    # Повторное подтверждение — конфликт и никакого второго следа в аудите.
    with pytest.raises(ConflictError):
        confirm_income(chief, transaction_id=tx.id)
    assert logs.count() == 1


# --- API /api/v1/audit/ ---


def test_audit_api_available_to_chief_with_action_filter(api, auth, chief, accountant, business):
    tx = create_income(
        accountant, business=business, amount=D("100.00"), method="cash"
    )
    confirm_income(chief, transaction_id=tx.id)

    auth(api, chief)
    resp = api.get("/api/v1/audit/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert {r["action"] for r in data["results"]} == {
        "transaction.income_created",
        "transaction.income_confirmed",
    }

    filtered = api.get("/api/v1/audit/", {"action": "transaction.income_created"})
    assert filtered.status_code == 200
    rows = filtered.json()["results"]
    assert len(rows) == 1
    row = rows[0]
    assert row["action"] == "transaction.income_created"
    assert row["actor"] == accountant.id
    assert row["actor_name"] == str(accountant)
    assert row["entity_type"] == "Transaction"
    assert row["entity_id"] == str(tx.id)


def test_audit_api_forbidden_for_cashier(api, auth, cashier):
    auth(api, cashier)
    resp = api.get("/api/v1/audit/")
    assert resp.status_code == 403
    assert resp.json()["code"] == "permission_denied"


def test_audit_api_requires_auth(api):
    resp = api.get("/api/v1/audit/")
    assert resp.status_code == 401
    assert resp.json()["code"] == "not_authenticated"
