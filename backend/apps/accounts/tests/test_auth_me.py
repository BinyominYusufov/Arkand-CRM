"""Аутентификация и профиль: JWT-поток, /api/v1/me, формат ошибок 401."""
import pytest

from apps.core import rbac
from apps.testing import factories as f

pytestmark = pytest.mark.django_db


# --- /api/v1/me ---


def test_me_returns_role_permissions_businesses_and_registers(api, auth):
    b1 = f.BusinessFactory()
    f.BusinessFactory()  # чужой бизнес — не должен попасть в ответ
    cashier = f.CashierFactory(business=b1)
    register = f.CashRegisterFactory(business=b1)
    register.members.add(cashier)
    f.CashRegisterFactory(business=b1)  # чужая касса

    auth(api, cashier)
    resp = api.get("/api/v1/me")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == cashier.id
    assert data["email"] == cashier.email
    assert data["role"] == "cashier"
    assert data["permissions"] == sorted(["cash.view", "cash.operate"])
    assert [b["id"] for b in data["businesses"]] == [b1.id]
    assert data["business"]["id"] == b1.id
    assert data["cash_register_ids"] == [register.id]


def test_me_owner_sees_all_active_businesses_and_overlay_perm(api, auth, owner_user):
    b1 = f.BusinessFactory()
    b2 = f.BusinessFactory()
    f.BusinessFactory(is_active=False)

    auth(api, owner_user)
    data = api.get("/api/v1/me").json()

    assert data["role"] == "owner"
    assert data["permissions"] == sorted(rbac.DEFAULT_ROLE_PERMISSIONS["owner"])
    assert rbac.PERM_OVERLAY_VIEW in data["permissions"]
    assert rbac.PERM_FINANCE_MANAGE not in data["permissions"]
    assert {b["id"] for b in data["businesses"]} == {b1.id, b2.id}
    assert data["business"] is None
    assert data["cash_register_ids"] == []


# --- JWT-поток ---


def test_jwt_obtain_access_and_refresh(api):
    user = f.AccountantFactory(password="Secret123!")
    resp = api.post(
        "/api/v1/auth/token",
        {"email": user.email, "password": "Secret123!"},
        format="json",
    )
    assert resp.status_code == 200
    tokens = resp.json()
    assert tokens["access"]
    assert tokens["refresh"]

    # Access-токен реально открывает защищённый endpoint.
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    me = api.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["id"] == user.id

    # Refresh выдаёт новый access.
    api.credentials()
    refreshed = api.post(
        "/api/v1/auth/refresh", {"refresh": tokens["refresh"]}, format="json"
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access"]


def test_jwt_login_email_case_insensitive(api):
    user = f.AccountantFactory(password="Secret123!")
    resp = api.post(
        "/api/v1/auth/token",
        {"email": user.email.upper(), "password": "Secret123!"},
        format="json",
    )
    assert resp.status_code == 200


def test_jwt_wrong_password_returns_401(api):
    user = f.AccountantFactory(password="Secret123!")
    resp = api.post(
        "/api/v1/auth/token",
        {"email": user.email, "password": "wrong-password"},
        format="json",
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "not_authenticated"
    assert set(body) == {"code", "message", "details"}


@pytest.mark.parametrize(
    "path",
    ["/api/v1/me", "/api/v1/businesses/", "/api/v1/reports/cashflow", "/api/v1/audit/"],
)
def test_protected_endpoints_require_token(api, path):
    resp = api.get(path)
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "not_authenticated"
    assert body["message"] == "Требуется аутентификация"


def test_stale_or_garbage_token_returns_401(api):
    api.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")
    resp = api.get("/api/v1/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "not_authenticated"
