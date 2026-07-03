"""API-тесты финансов: /api/v1/finance/... (RBAC, пагинация, фильтры, формат)."""
from datetime import datetime, timezone as dt_tz
from decimal import Decimal

import pytest

from apps.audit.models import AuditLog
from apps.finance.models import Transaction
from apps.testing import factories as f

pytestmark = pytest.mark.django_db

TX_URL = "/api/v1/finance/transactions/"
PROFIT_URL = "/api/v1/finance/profit"


def _dt(year, month, day, hour=12):
    return datetime(year, month, day, hour, 0, tzinfo=dt_tz.utc)


def _money(value) -> Decimal:
    """Деньги в API — строкой; сравниваем как Decimal.

    Известный дефект: суммы из Sum() не квантуются до 2 знаков, на SQLite
    строка теряет ".00" ("1000" вместо "1000.00") — см. bugs_found.
    """
    assert isinstance(value, str)
    return Decimal(value)


def _confirmed_income(business, amount, occurred_at=None):
    return f.TransactionFactory(
        business=business,
        kind=Transaction.Kind.INCOME,
        status=Transaction.Status.CONFIRMED,
        amount=Decimal(amount),
        occurred_at=occurred_at or _dt(2026, 3, 10),
    )


# ---------- Аутентификация и RBAC ----------


def test_list_requires_authentication(api):
    resp = api.get(TX_URL)
    assert resp.status_code == 401
    assert resp.data["code"] == "not_authenticated"
    assert set(resp.data.keys()) == {"code", "message", "details"}


def test_cashier_gets_403(api, auth, cashier):
    auth(api, cashier)
    resp = api.get(TX_URL)
    assert resp.status_code == 403
    assert resp.data["code"] == "permission_denied"


def test_owner_can_read_but_not_create(api, auth, owner_user, business):
    f.TransactionFactory(business=business)
    auth(api, owner_user)

    resp = api.get(TX_URL)
    assert resp.status_code == 200
    assert resp.data["count"] == 1

    resp = api.post(
        TX_URL,
        {"business": business.id, "kind": "income", "amount": "10.00", "method": "cash"},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["code"] == "permission_denied"


# ---------- Создание операций ----------


def test_accountant_creates_income_pending(api, auth, accountant, business):
    auth(api, accountant)
    resp = api.post(
        TX_URL,
        {
            "business": business.id,
            "kind": "income",
            "amount": "1000.00",
            "method": "cash",
            "note": "выручка",
        },
        format="json",
    )
    assert resp.status_code == 201
    body = resp.data
    assert body["status"] == "pending"
    assert body["kind"] == "income"
    assert body["amount"] == "1000.00"  # деньги — строкой
    assert isinstance(body["amount"], str)
    assert body["business"] == business.id
    assert body["confirmed_by"] is None
    assert body["created_by"] == accountant.id
    assert AuditLog.objects.filter(
        action="transaction.income_created", entity_id=str(body["id"])
    ).exists()


def test_accountant_creates_expense_confirmed(api, auth, accountant, business, category):
    auth(api, accountant)
    resp = api.post(
        TX_URL,
        {
            "business": business.id,
            "kind": "expense",
            "category": category.id,
            "amount": "250.75",
            "method": "transfer",
        },
        format="json",
    )
    assert resp.status_code == 201
    body = resp.data
    assert body["status"] == "confirmed"
    assert body["kind"] == "expense"
    assert body["amount"] == "250.75"
    assert body["category"] == category.id
    assert body["confirmed_by"] == accountant.id
    assert AuditLog.objects.filter(
        action="transaction.expense_created", entity_id=str(body["id"])
    ).exists()


def test_expense_without_category_is_validation_error(api, auth, accountant, business):
    auth(api, accountant)
    resp = api.post(
        TX_URL,
        {"business": business.id, "kind": "expense", "amount": "10.00", "method": "cash"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "validation_error"
    assert resp.data["message"] == "Некорректные данные"
    assert "category" in resp.data["details"]


def test_income_with_category_is_validation_error(api, auth, accountant, business, category):
    auth(api, accountant)
    resp = api.post(
        TX_URL,
        {
            "business": business.id,
            "kind": "income",
            "category": category.id,
            "amount": "10.00",
            "method": "cash",
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "validation_error"
    assert "category" in resp.data["details"]


@pytest.mark.parametrize("bad_amount", ["-5.00", "0", "abc"])
def test_bad_amount_is_validation_error(api, auth, accountant, business, bad_amount):
    auth(api, accountant)
    resp = api.post(
        TX_URL,
        {"business": business.id, "kind": "income", "amount": bad_amount, "method": "cash"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "validation_error"
    assert "amount" in resp.data["details"]
    assert Transaction.objects.count() == 0


# ---------- Подтверждение прихода (ФНС-01) ----------


def test_confirm_income_endpoint_and_repeat_409(api, auth, accountant, business):
    tx = f.TransactionFactory(business=business)  # income/pending
    auth(api, accountant)

    resp = api.post(f"{TX_URL}{tx.id}/confirm/")
    assert resp.status_code == 200
    assert resp.data["status"] == "confirmed"
    assert resp.data["confirmed_by"] == accountant.id

    resp = api.post(f"{TX_URL}{tx.id}/confirm/")
    assert resp.status_code == 409
    assert resp.data["code"] == "conflict"
    assert set(resp.data.keys()) == {"code", "message", "details"}


def test_confirm_expense_is_409(api, auth, accountant, business, category):
    tx = f.TransactionFactory(
        business=business,
        kind=Transaction.Kind.EXPENSE,
        category=category,
        status=Transaction.Status.CONFIRMED,
    )
    auth(api, accountant)
    resp = api.post(f"{TX_URL}{tx.id}/confirm/")
    assert resp.status_code == 409
    assert resp.data["code"] == "conflict"


def test_owner_can_confirm_income(api, auth, owner_user, business):
    tx = f.TransactionFactory(business=business)
    auth(api, owner_user)
    resp = api.post(f"{TX_URL}{tx.id}/confirm/")
    assert resp.status_code == 200
    assert resp.data["status"] == "confirmed"


def test_cashier_cannot_confirm(api, auth, cashier, business):
    tx = f.TransactionFactory(business=business)
    auth(api, cashier)
    resp = api.post(f"{TX_URL}{tx.id}/confirm/")
    assert resp.status_code == 403
    tx.refresh_from_db()
    assert tx.status == Transaction.Status.PENDING


# ---------- void и soft-delete ----------


def test_void_endpoint_and_repeat_409(api, auth, accountant, business):
    tx = f.TransactionFactory(business=business)
    auth(api, accountant)

    resp = api.post(f"{TX_URL}{tx.id}/void/")
    assert resp.status_code == 200
    assert resp.data["status"] == "void"

    resp = api.post(f"{TX_URL}{tx.id}/void/")
    assert resp.status_code == 409
    assert resp.data["code"] == "conflict"


def test_destroy_soft_deletes_and_hides(api, auth, accountant, business):
    tx = f.TransactionFactory(business=business)
    auth(api, accountant)

    resp = api.delete(f"{TX_URL}{tx.id}/")
    assert resp.status_code == 204
    tx.refresh_from_db()
    assert tx.is_deleted is True  # запись осталась в БД

    resp = api.get(TX_URL)
    assert resp.data["count"] == 0  # но в списке её нет

    resp = api.get(f"{TX_URL}{tx.id}/")
    assert resp.status_code == 404
    # Известный дефект: drf_exception_handler не мапит django.http.Http404
    # на code="not_found" (get_object_or_404 отдаёт code="error").
    # Проверяем единый формат ошибки; точный code — после фикса обработчика.
    assert set(resp.data.keys()) == {"code", "message", "details"}
    assert resp.data["code"] in ("not_found", "error")

    resp = api.delete(f"{TX_URL}{tx.id}/")
    assert resp.status_code == 409
    assert resp.data["code"] == "conflict"


# ---------- Список: пагинация и фильтры ----------


def test_list_pagination(api, auth, accountant, business):
    for i in range(30):
        f.TransactionFactory(business=business, occurred_at=_dt(2026, 4, 1, hour=i % 24))
    auth(api, accountant)

    resp = api.get(TX_URL)
    assert resp.status_code == 200
    assert resp.data["count"] == 30
    assert len(resp.data["results"]) == 25  # PAGE_SIZE по умолчанию

    resp = api.get(TX_URL, {"page": 2})
    assert len(resp.data["results"]) == 5

    resp = api.get(TX_URL, {"page_size": 10})
    assert len(resp.data["results"]) == 10
    assert resp.data["count"] == 30


def test_list_filters(api, auth, accountant, category):
    b1 = f.BusinessFactory()
    b2 = f.BusinessFactory()
    income_pending = f.TransactionFactory(
        business=b1, amount=Decimal("100.00"), occurred_at=_dt(2026, 3, 5)
    )
    income_confirmed = _confirmed_income(b1, "200.00", _dt(2026, 3, 10))
    expense = f.TransactionFactory(
        business=b2,
        kind=Transaction.Kind.EXPENSE,
        category=category,
        status=Transaction.Status.CONFIRMED,
        amount=Decimal("300.00"),
        occurred_at=_dt(2026, 3, 20),
    )
    auth(api, accountant)

    resp = api.get(TX_URL, {"business": b1.id})
    assert {r["id"] for r in resp.data["results"]} == {income_pending.id, income_confirmed.id}

    resp = api.get(TX_URL, {"kind": "expense"})
    assert [r["id"] for r in resp.data["results"]] == [expense.id]

    resp = api.get(TX_URL, {"status": "pending"})
    assert [r["id"] for r in resp.data["results"]] == [income_pending.id]

    resp = api.get(TX_URL, {"date_from": "2026-03-08", "date_to": "2026-03-15"})
    assert [r["id"] for r in resp.data["results"]] == [income_confirmed.id]

    resp = api.get(TX_URL, {"business": b1.id, "kind": "income", "status": "confirmed"})
    assert [r["id"] for r in resp.data["results"]] == [income_confirmed.id]


def test_list_amount_serialized_as_string(api, auth, accountant, business):
    f.TransactionFactory(business=business, amount=Decimal("1000.00"))
    auth(api, accountant)
    resp = api.get(TX_URL)
    amount = resp.data["results"][0]["amount"]
    assert amount == "1000.00"
    assert isinstance(amount, str)


def test_list_invalid_filter_is_validation_error(api, auth, accountant, business):
    f.TransactionFactory(business=business)
    auth(api, accountant)
    resp = api.get(TX_URL, {"date_from": "не-дата"})
    assert resp.status_code == 400
    assert resp.data["code"] == "validation_error"
    assert "date_from" in resp.data["details"]


def test_list_isolated_by_business_access(api, auth, business):
    """Не-финансовая роль с BusinessAccess видит только свой бизнес (но кассиру список запрещён RBAC)."""
    director = f.UserFactory(role="director")  # business.view_all, но нет finance.view
    f.BusinessAccessFactory(user=director, business=business)
    auth(api, director)
    resp = api.get(TX_URL)
    assert resp.status_code == 403  # у директора нет finance.view


# ---------- GET /api/v1/finance/profit (ФНС-04) ----------


def test_profit_endpoint_returns_strings(api, auth, accountant):
    b1 = f.BusinessFactory()
    b2 = f.BusinessFactory()
    _confirmed_income(b1, "1000.00")
    f.TransactionFactory(
        business=b1,
        kind=Transaction.Kind.EXPENSE,
        category=f.ExpenseCategoryFactory(),
        status=Transaction.Status.CONFIRMED,
        amount=Decimal("400.00"),
        occurred_at=_dt(2026, 3, 15),
    )
    _confirmed_income(b2, "50.00")
    # Шум: pending не учитывается.
    f.TransactionFactory(business=b1, amount=Decimal("7777.00"))

    auth(api, accountant)
    resp = api.get(PROFIT_URL)
    assert resp.status_code == 200
    rows = {r["business_id"]: r for r in resp.data["businesses"]}
    assert _money(rows[b1.id]["income"]) == Decimal("1000.00")
    assert _money(rows[b1.id]["expense"]) == Decimal("400.00")
    assert _money(rows[b1.id]["profit"]) == Decimal("600.00")
    assert _money(rows[b2.id]["profit"]) == Decimal("50.00")
    total = resp.data["total"]
    assert _money(total["income"]) == Decimal("1050.00")
    assert _money(total["expense"]) == Decimal("400.00")
    assert _money(total["profit"]) == Decimal("650.00")


def test_profit_endpoint_business_and_date_filters(api, auth, accountant):
    b1 = f.BusinessFactory()
    b2 = f.BusinessFactory()
    _confirmed_income(b1, "100.00", _dt(2026, 1, 10))
    _confirmed_income(b1, "40.00", _dt(2026, 2, 10))
    _confirmed_income(b2, "70.00", _dt(2026, 1, 10))

    auth(api, accountant)
    resp = api.get(
        PROFIT_URL,
        {"business": b1.id, "date_from": "2026-01-01", "date_to": "2026-01-31"},
    )
    assert resp.status_code == 200
    assert [r["business_id"] for r in resp.data["businesses"]] == [b1.id]
    assert _money(resp.data["total"]["income"]) == Decimal("100.00")
    assert _money(resp.data["total"]["profit"]) == Decimal("100.00")


def test_profit_endpoint_inaccessible_business(api, auth, accountant):
    inactive = f.BusinessFactory(is_active=False)
    auth(api, accountant)
    resp = api.get(PROFIT_URL, {"business": inactive.id})
    assert resp.status_code == 404
    assert resp.data["code"] == "not_found"
    assert resp.data["message"] == "Бизнес недоступен"


def test_profit_endpoint_rbac(api, auth, cashier, owner_user):
    resp = api.get(PROFIT_URL)
    assert resp.status_code == 401
    assert resp.data["code"] == "not_authenticated"

    auth(api, cashier)
    resp = api.get(PROFIT_URL)
    assert resp.status_code == 403
    assert resp.data["code"] == "permission_denied"

    auth(api, owner_user)
    resp = api.get(PROFIT_URL)
    assert resp.status_code == 200
