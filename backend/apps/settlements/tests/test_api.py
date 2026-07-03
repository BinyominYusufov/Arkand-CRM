"""API-тесты взаиморасчётов: /api/v1/settlements/* (RBAC, формат ошибок, деньги строками)."""
from decimal import Decimal

import pytest

from apps.audit.models import AuditLog
from apps.settlements import services
from apps.settlements.models import Barter, Debt, DebtSettlement, Transfer
from apps.testing import factories as f

pytestmark = pytest.mark.django_db

BASE = "/api/v1/settlements"


# --- Реестр долгов (БАР-02) ---
def test_registry_money_as_strings(api, auth, accountant):
    b1, b2 = f.BusinessFactory(name="Завод"), f.BusinessFactory(name="Салон")
    debt = f.DebtFactory(debtor=b1, creditor=b2, amount=Decimal("10000.00"))
    services.settle_debt(
        accountant,
        debt_id=debt.pk,
        method=DebtSettlement.Method.RETURN,
        amount=Decimal("4000.00"),
    )

    resp = auth(api, accountant).get(f"{BASE}/debts/registry/")
    assert resp.status_code == 200
    data = resp.data

    row = next(r for r in data["debts"] if r["id"] == debt.pk)
    assert row["amount"] == "10000.00"
    assert row["remaining"] == "6000.00"
    assert row["debtor_name"] == "Завод"
    assert row["creditor_name"] == "Салон"
    assert row["is_overdue"] is False

    pair = data["pairs"][0]
    assert pair["total_remaining"] == "6000.00"
    assert pair["debts_count"] == 1
    assert data["total_open"] == "6000.00"


# --- Передачи через API ---
def test_create_and_approve_transfer_api(api, auth, accountant):
    src, dst = f.BusinessFactory(), f.BusinessFactory()
    client = auth(api, accountant)

    resp = client.post(
        f"{BASE}/transfers/",
        {"from_business": src.pk, "to_business": dst.pk, "amount": "5000.00"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["amount"] == "5000.00"  # деньги строкой
    assert resp.data["status"] == "pending"
    assert resp.data["requires_owner_approval"] is False
    tr_id = resp.data["id"]

    resp = client.post(f"{BASE}/transfers/{tr_id}/approve/")
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"
    assert resp.data["approved_by"] == accountant.pk

    # БАР-01/ХОЛ-30: авто-долг получатель → отправитель.
    debt = Debt.objects.get(source_transfer_id=tr_id)
    assert debt.debtor == dst and debt.creditor == src
    assert debt.amount == Decimal("5000.00")
    assert AuditLog.objects.filter(
        action="transfer.approved", entity_id=str(tr_id)
    ).exists()

    # Двойное одобрение -> 409 в едином формате ошибки.
    resp = client.post(f"{BASE}/transfers/{tr_id}/approve/")
    assert resp.status_code == 409
    assert resp.data["code"] == "conflict"
    assert "message" in resp.data and "details" in resp.data
    assert Debt.objects.filter(source_transfer_id=tr_id).count() == 1


def test_reject_transfer_api_and_repeat(api, auth, chief):
    tr = f.TransferFactory()
    client = auth(api, chief)

    resp = client.post(f"{BASE}/transfers/{tr.pk}/reject/")
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"
    assert Debt.objects.count() == 0

    resp = client.post(f"{BASE}/transfers/{tr.pk}/reject/")
    assert resp.status_code == 409
    assert resp.data["code"] == "conflict"


def test_transfer_self_rejected_by_api(api, auth, accountant, business):
    resp = auth(api, accountant).post(
        f"{BASE}/transfers/",
        {"from_business": business.pk, "to_business": business.pk, "amount": "10.00"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "validation_error"


# --- ХОЛ-32 через API ---
def test_owner_threshold_via_api(api, auth, accountant, owner_user):
    src, dst = f.BusinessFactory(), f.BusinessFactory()
    client = auth(api, accountant)

    resp = client.post(
        f"{BASE}/transfers/",
        {"from_business": src.pk, "to_business": dst.pk, "amount": "50000.01"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["requires_owner_approval"] is True
    tr_id = resp.data["id"]

    # Бухгалтер сверх порога — 403 с доменным кодом.
    resp = client.post(f"{BASE}/transfers/{tr_id}/approve/")
    assert resp.status_code == 403
    assert resp.data["code"] == "owner_approval_required"
    assert resp.data["details"]["threshold"] == "50000"
    assert Transfer.objects.get(pk=tr_id).status == Transfer.Status.PENDING

    # Владелец — успех.
    resp = auth(api, owner_user).post(f"{BASE}/transfers/{tr_id}/approve/")
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"
    assert Debt.objects.filter(source_transfer_id=tr_id).exists()


# --- Погашение долга через API (БАР-03) ---
def test_settle_debt_api_partial_then_full(api, auth, accountant):
    debt = f.DebtFactory(amount=Decimal("5000.00"))
    client = auth(api, accountant)

    resp = client.post(
        f"{BASE}/debts/{debt.pk}/settle/",
        {"method": "return", "amount": "2000.00"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "open"
    assert resp.data["remaining"] == "3000.00"
    assert resp.data["amount"] == "5000.00"

    # Без amount — гасится остаток целиком.
    resp = client.post(
        f"{BASE}/debts/{debt.pk}/settle/", {"method": "offset"}, format="json"
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "closed"
    assert resp.data["remaining"] == "0.00"
    assert resp.data["closed_at"] is not None
    assert len(resp.data["settlements"]) == 2
    assert AuditLog.objects.filter(
        action="debt.settled", entity_id=str(debt.pk)
    ).count() == 2

    # Погашение закрытого -> 409.
    resp = client.post(
        f"{BASE}/debts/{debt.pk}/settle/",
        {"method": "return", "amount": "1.00"},
        format="json",
    )
    assert resp.status_code == 409
    assert resp.data["code"] == "conflict"


def test_settle_debt_api_exceeds_remaining(api, auth, accountant):
    debt = f.DebtFactory(amount=Decimal("1000.00"))
    resp = auth(api, accountant).post(
        f"{BASE}/debts/{debt.pk}/settle/",
        {"method": "return", "amount": "1000.01"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "settlement_exceeds_debt"
    assert resp.data["details"] == {"remaining": "1000.00", "attempted": "1000.01"}


# --- Неттинг через API (ХОЛ-31) ---
def test_net_debts_api(api, auth, accountant):
    a, b = f.BusinessFactory(), f.BusinessFactory()
    f.DebtFactory(debtor=a, creditor=b, amount=Decimal("30000.00"))
    f.DebtFactory(debtor=b, creditor=a, amount=Decimal("18000.00"))

    resp = auth(api, accountant).post(
        f"{BASE}/net", {"business_a": a.pk, "business_b": b.pk}, format="json"
    )
    assert resp.status_code == 200
    assert resp.data["netted_amount"] == "18000.00"
    assert resp.data["remaining_a_to_b"] == "12000.00"
    assert resp.data["remaining_b_to_a"] == "0.00"
    assert AuditLog.objects.filter(action="debts.netted").exists()

    # Повтор без встречных долгов -> 400 nothing_to_net.
    resp = auth(api, accountant).post(
        f"{BASE}/net", {"business_a": a.pk, "business_b": b.pk}, format="json"
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "nothing_to_net"


# --- Бартер через API ---
def test_barter_api_create_and_close_debt(api, auth, accountant, cashier):
    a, b = f.BusinessFactory(), f.BusinessFactory()
    client = auth(api, accountant)

    # Контролёр-кассир запрещён бизнес-правилом.
    resp = client.post(
        f"{BASE}/barters/",
        {
            "business_a": a.pk,
            "business_b": b.pk,
            "description": "цемент за дрова",
            "value": "3000.00",
            "controlled_by": cashier.pk,
        },
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["code"] == "barter_controller_role"
    assert Barter.objects.count() == 0

    resp = client.post(
        f"{BASE}/barters/",
        {
            "business_a": a.pk,
            "business_b": b.pk,
            "description": "цемент за дрова",
            "value": "3000.00",
            "controlled_by": accountant.pk,
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["value"] == "3000.00"
    assert resp.data["status"] == "active"
    barter_id = resp.data["id"]

    debt = f.DebtFactory(debtor=a, creditor=b, amount=Decimal("5000.00"))
    resp = client.post(
        f"{BASE}/barters/{barter_id}/close-debt/", {"debt": debt.pk}, format="json"
    )
    assert resp.status_code == 200
    assert resp.data["remaining"] == "2000.00"
    assert resp.data["status"] == "open"
    assert Barter.objects.get(pk=barter_id).status == Barter.Status.COMPLETED
    assert AuditLog.objects.filter(
        action="barter.closed_debt", entity_id=str(barter_id)
    ).exists()

    # Бартер уже завершён -> 409.
    resp = client.post(
        f"{BASE}/barters/{barter_id}/close-debt/", {"debt": debt.pk}, format="json"
    )
    assert resp.status_code == 409
    assert resp.data["code"] == "conflict"


def test_barter_complete_cancel_api(api, auth, chief):
    barter = f.BarterFactory()
    client = auth(api, chief)

    resp = client.post(f"{BASE}/barters/{barter.pk}/complete/")
    assert resp.status_code == 200
    assert resp.data["status"] == "completed"

    resp = client.post(f"{BASE}/barters/{barter.pk}/cancel/")
    assert resp.status_code == 409
    assert resp.data["code"] == "conflict"


# --- RBAC ---
def test_cashier_denied_everywhere(api, auth, cashier):
    tr = f.TransferFactory()
    debt = f.DebtFactory()
    client = auth(api, cashier)

    for method, url, payload in [
        ("get", f"{BASE}/transfers/", None),
        ("get", f"{BASE}/debts/registry/", None),
        ("post", f"{BASE}/transfers/", {"amount": "1.00"}),
        ("post", f"{BASE}/transfers/{tr.pk}/approve/", None),
        ("post", f"{BASE}/transfers/{tr.pk}/reject/", None),
        ("post", f"{BASE}/debts/{debt.pk}/settle/", {"method": "return"}),
        ("post", f"{BASE}/net", {}),
        ("post", f"{BASE}/barters/", {}),
    ]:
        resp = getattr(client, method)(url, payload, format="json")
        assert resp.status_code == 403, url
        assert resp.data["code"] == "permission_denied", url

    tr.refresh_from_db()
    assert tr.status == Transfer.Status.PENDING


def test_owner_reads_and_approves_but_cannot_create(api, auth, owner_user):
    tr = f.TransferFactory(amount=Decimal("60000.00"), requires_owner_approval=True)
    src, dst = tr.from_business, tr.to_business
    client = auth(api, owner_user)

    # Чтение доступно.
    assert client.get(f"{BASE}/transfers/").status_code == 200
    assert client.get(f"{BASE}/debts/registry/").status_code == 200
    assert client.get(f"{BASE}/debts/").status_code == 200

    # Создание передачи — только финотдел (settlements.manage).
    resp = client.post(
        f"{BASE}/transfers/",
        {"from_business": src.pk, "to_business": dst.pk, "amount": "100.00"},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["code"] == "permission_denied"

    # Одобрение (settlements.approve) — доступно, даже сверх порога.
    resp = client.post(f"{BASE}/transfers/{tr.pk}/approve/")
    assert resp.status_code == 200
    assert resp.data["status"] == "approved"


def test_anonymous_gets_401(api):
    resp = api.get(f"{BASE}/debts/registry/")
    assert resp.status_code == 401
    assert resp.data["code"] == "not_authenticated"
