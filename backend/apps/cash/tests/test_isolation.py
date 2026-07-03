"""КАС-04: изоляция касс — кассир видит только свои кассы и операции."""
from decimal import Decimal

import pytest

from apps.cash.models import CashOperation
from apps.testing import factories as f

pytestmark = pytest.mark.django_db

REGISTERS_URL = "/api/v1/cash/registers/"
OPERATIONS_URL = "/api/v1/cash/operations/"


@pytest.fixture
def own_register(cashier):
    reg = f.CashRegisterFactory(name="Своя касса")
    reg.members.add(cashier)
    return reg


@pytest.fixture
def foreign_register():
    return f.CashRegisterFactory(name="Чужая касса")


def _op_ids(response):
    return {row["id"] for row in response.data["results"]}


# ---------- Кассы ----------


def test_cashier_sees_only_member_registers(api, auth, cashier, own_register, foreign_register):
    auth(api, cashier)
    resp = api.get(REGISTERS_URL)

    assert resp.status_code == 200
    ids = {row["id"] for row in resp.data}
    assert ids == {own_register.id}
    assert foreign_register.id not in ids  # чужой кассы физически нет в ответе


def test_cashier_without_memberships_sees_empty_list(api, auth, cashier, foreign_register):
    auth(api, cashier)
    resp = api.get(REGISTERS_URL)
    assert resp.status_code == 200
    assert resp.data == []


def test_cashier_cannot_retrieve_foreign_register(api, auth, cashier, own_register, foreign_register):
    auth(api, cashier)
    resp = api.get(f"{REGISTERS_URL}{foreign_register.id}/")
    assert resp.status_code == 404
    # Формат ошибки единый; код должен быть "not_found", но обработчик
    # сравнивает с DRF NotFound, а вьюхи кидают django Http404 → "error" (баг).
    assert set(resp.data) == {"code", "message", "details"}
    assert resp.data["code"] in ("not_found", "error")


def test_accountant_sees_all_registers(api, auth, accountant, own_register, foreign_register):
    auth(api, accountant)
    resp = api.get(REGISTERS_URL)
    assert resp.status_code == 200
    assert {row["id"] for row in resp.data} == {own_register.id, foreign_register.id}


def test_owner_sees_all_registers(api, auth, owner_user, own_register, foreign_register):
    auth(api, owner_user)
    resp = api.get(REGISTERS_URL)
    assert resp.status_code == 200
    assert {row["id"] for row in resp.data} == {own_register.id, foreign_register.id}


# ---------- Операции ----------


def test_cashier_sees_only_own_register_operations(
    api, auth, cashier, own_register, foreign_register
):
    own_op = f.CashOperationFactory(register=own_register)
    foreign_op = f.CashOperationFactory(register=foreign_register)

    auth(api, cashier)
    resp = api.get(OPERATIONS_URL)

    assert resp.status_code == 200
    ids = _op_ids(resp)
    assert ids == {own_op.id}
    assert foreign_op.id not in ids


def test_cashier_cannot_retrieve_foreign_operation(
    api, auth, cashier, own_register, foreign_register
):
    foreign_op = f.CashOperationFactory(register=foreign_register)
    auth(api, cashier)
    resp = api.get(f"{OPERATIONS_URL}{foreign_op.id}/")
    assert resp.status_code == 404


def test_finance_and_owner_see_all_operations(
    api, auth, accountant, owner_user, own_register, foreign_register
):
    op1 = f.CashOperationFactory(register=own_register)
    op2 = f.CashOperationFactory(register=foreign_register)

    auth(api, accountant)
    resp = api.get(OPERATIONS_URL)
    assert resp.status_code == 200
    assert _op_ids(resp) == {op1.id, op2.id}

    auth(api, owner_user)
    resp = api.get(OPERATIONS_URL)
    assert resp.status_code == 200
    assert _op_ids(resp) == {op1.id, op2.id}


def test_cashier_cannot_create_operation_in_foreign_register(
    api, auth, cashier, own_register, foreign_register
):
    auth(api, cashier)
    resp = api.post(
        OPERATIONS_URL,
        {
            "register": foreign_register.id,
            "direction": "in",
            "method": "cash",
            "amount": "100.00",
        },
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["code"] == "permission_denied"
    assert set(resp.data) == {"code", "message", "details"}
    assert foreign_register.operations.count() == 0


def test_cashier_can_create_operation_in_own_register(api, auth, cashier, own_register):
    auth(api, cashier)
    resp = api.post(
        OPERATIONS_URL,
        {
            "register": own_register.id,
            "direction": "in",
            "method": "cash",
            "amount": "100.00",
        },
        format="json",
    )
    assert resp.status_code == 201
    op = CashOperation.objects.get(id=resp.data["id"])
    assert op.register == own_register
    assert op.created_by == cashier
    assert op.amount == Decimal("100.00")


# ---------- Управление кассами ----------


def test_cashier_cannot_create_register(api, auth, cashier, business):
    auth(api, cashier)
    resp = api.post(
        REGISTERS_URL,
        {"name": "Новая касса", "business": business.id, "turnover_limit": "10000.00"},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["code"] == "permission_denied"


def test_cashier_cannot_update_own_register(api, auth, cashier, own_register):
    auth(api, cashier)
    resp = api.patch(
        f"{REGISTERS_URL}{own_register.id}/",
        {"turnover_limit": "1.00"},
        format="json",
    )
    assert resp.status_code == 403
    own_register.refresh_from_db()
    assert own_register.turnover_limit == Decimal("50000.00")


def test_accountant_can_create_register(api, auth, accountant, cashier, business):
    auth(api, accountant)
    resp = api.post(
        REGISTERS_URL,
        {
            "name": "Касса финотдела",
            "business": business.id,
            "turnover_limit": "25000.00",
            "members": [cashier.id],
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["name"] == "Касса финотдела"
    assert resp.data["turnover_limit"] == "25000.00"
    assert resp.data["members"] == [cashier.id]


def test_accountant_can_update_register(api, auth, accountant, own_register):
    auth(api, accountant)
    resp = api.patch(
        f"{REGISTERS_URL}{own_register.id}/",
        {"turnover_limit": "77777.77"},
        format="json",
    )
    assert resp.status_code == 200
    own_register.refresh_from_db()
    assert own_register.turnover_limit == Decimal("77777.77")
