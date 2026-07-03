"""Overlay (Часть 7): доступ только владельцам, консистентность сводки, экспорт."""
from decimal import Decimal

import pytest

from apps.finance.models import Transaction
from apps.testing import factories as f

pytestmark = pytest.mark.django_db

D = Decimal

OVERLAY_PATHS = [
    "/api/v1/overlay/summary",
    "/api/v1/overlay/cash",
    "/api/v1/overlay/debts",
    "/api/v1/overlay/payroll",
    "/api/v1/overlay/export",
]


def confirmed_tx(business, kind, amount, category=None):
    return f.TransactionFactory(
        business=business,
        kind=kind,
        amount=D(amount),
        category=category,
        status=Transaction.Status.CONFIRMED,
    )


# --- Права доступа ---


@pytest.mark.parametrize("path", OVERLAY_PATHS)
def test_owner_gets_200(api, auth, owner_user, path):
    auth(api, owner_user)
    assert api.get(path).status_code == 200


@pytest.mark.parametrize("path", OVERLAY_PATHS)
@pytest.mark.parametrize("role_fixture", ["chief", "accountant", "cashier"])
def test_non_owners_get_403(api, auth, request, role_fixture, path):
    user = request.getfixturevalue(role_fixture)
    auth(api, user)
    resp = api.get(path)
    assert resp.status_code == 403
    assert resp.json()["code"] == "permission_denied"


@pytest.mark.parametrize("path", OVERLAY_PATHS)
def test_anonymous_gets_401(api, path):
    resp = api.get(path)
    assert resp.status_code == 401
    assert resp.json()["code"] == "not_authenticated"


# --- Консистентность сводки ---


def test_summary_totals_consistent_with_businesses(api, auth, owner_user, category):
    b1 = f.BusinessFactory()
    b2 = f.BusinessFactory()
    confirmed_tx(b1, Transaction.Kind.INCOME, "1000.00")
    confirmed_tx(b1, Transaction.Kind.EXPENSE, "400.00", category=category)
    confirmed_tx(b2, Transaction.Kind.INCOME, "2000.00")
    confirmed_tx(b2, Transaction.Kind.EXPENSE, "500.00", category=category)
    f.TransactionFactory(  # pending не считается
        business=b2, amount=D("5000.00"), status=Transaction.Status.PENDING
    )
    f.DebtFactory(debtor=b1, creditor=b2, amount=D("500.00"))
    register = f.CashRegisterFactory(business=b1)
    f.CashOperationFactory(register=register, direction="in", amount=D("250.00"))

    auth(api, owner_user)
    resp = api.get("/api/v1/overlay/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"]["income"] == "3000.00"
    assert data["total"]["expense"] == "900.00"
    assert data["total"]["profit"] == "2100.00"
    # total.income == сумма income по бизнесам.
    for key in ("income", "expense", "profit"):
        assert D(data["total"][key]) == sum(
            (D(r[key]) for r in data["businesses"]), D("0")
        )
        assert isinstance(data["total"][key], str)

    assert data["businesses_count"] == 2
    assert data["open_debts_total"] == "500.00"
    assert data["cash_balance_total"] == "250.00"


# --- Экспорт ---


def test_export_contract(api, auth, owner_user, category):
    b1 = f.BusinessFactory()
    confirmed_tx(b1, Transaction.Kind.INCOME, "1200.00")

    auth(api, owner_user)
    resp = api.get("/api/v1/overlay/export")
    assert resp.status_code == 200
    data = resp.json()

    assert data["format"] == "arkand.overlay"
    assert data["version"] == 1
    assert data["generated_at"]
    assert data["generated_for"] == owner_user.email
    assert set(data["data"]) == {"summary", "cash", "debts", "payroll"}
    assert data["data"]["summary"]["total"]["income"] == "1200.00"
    assert "registers" in data["data"]["cash"]
    assert "total_open" in data["data"]["debts"]
    assert "fund_total" in data["data"]["payroll"]
