"""RBAC Части 0: data-driven права, ролевая матрица, accessible_businesses,
API бизнесов (владелец пишет, остальные читают, DELETE = деактивация)."""
from decimal import Decimal

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.core import rbac
from apps.core import roles as R
from apps.core.models import Business, Role, RolePermission
from apps.finance import selectors as finance_selectors
from apps.finance.models import Transaction
from apps.testing import factories as f

pytestmark = pytest.mark.django_db


# --- Дефолтная ролевая матрица (fallback без записей в БД) ---


@pytest.mark.parametrize("factory", [f.ChiefFactory, f.AccountantFactory])
def test_finance_dept_has_manage_and_view_all(factory):
    user = factory()
    assert rbac.user_has_perm(user, rbac.PERM_FINANCE_MANAGE)
    assert rbac.user_has_perm(user, rbac.PERM_CASH_VIEW_ALL)
    assert rbac.user_has_perm(user, rbac.PERM_REPORTS_VIEW)
    # Overlay — только владельцы.
    assert not rbac.user_has_perm(user, rbac.PERM_OVERLAY_VIEW)


def test_owner_matrix(owner_user):
    assert rbac.user_has_perm(owner_user, rbac.PERM_FINANCE_APPROVE)
    assert rbac.user_has_perm(owner_user, rbac.PERM_OVERLAY_VIEW)
    assert rbac.user_has_perm(owner_user, rbac.PERM_BUSINESS_MANAGE)
    # Владелец контролирует, но не ведёт учёт.
    assert not rbac.user_has_perm(owner_user, rbac.PERM_FINANCE_MANAGE)
    assert not rbac.user_has_perm(owner_user, rbac.PERM_CASH_OPERATE)


def test_cashier_has_exactly_cash_view_and_operate(cashier):
    assert rbac.user_permissions(cashier) == sorted(
        [rbac.PERM_CASH_VIEW, rbac.PERM_CASH_OPERATE]
    )
    assert rbac.user_has_perm(cashier, rbac.PERM_CASH_VIEW)
    assert rbac.user_has_perm(cashier, rbac.PERM_CASH_OPERATE)
    assert not rbac.user_has_perm(cashier, rbac.PERM_FINANCE_VIEW)
    assert not rbac.user_has_perm(cashier, rbac.PERM_CASH_VIEW_ALL)


@pytest.mark.parametrize("role", [R.MANAGER, R.OPERATOR])
def test_manager_and_operator_have_no_perms(role):
    user = f.UserFactory(role=role)
    assert rbac.user_permissions(user) == []
    assert not rbac.user_has_perm(user, rbac.PERM_CASH_VIEW)
    assert not rbac.user_has_perm(user, rbac.PERM_FINANCE_VIEW)


# --- Data-driven: записи в БД перекрывают дефолт ---


def test_db_role_permissions_override_default_matrix():
    role = Role.objects.create(code=R.CASHIER, name="Кассир")
    RolePermission.objects.create(role=role, perm=rbac.PERM_FINANCE_VIEW)

    assert rbac.role_permissions(R.CASHIER) == frozenset({rbac.PERM_FINANCE_VIEW})

    cashier = f.CashierFactory()
    assert rbac.user_has_perm(cashier, rbac.PERM_FINANCE_VIEW)
    # Дефолтные cash.view / cash.operate перекрыты БД и пропали.
    assert not rbac.user_has_perm(cashier, rbac.PERM_CASH_VIEW)
    assert not rbac.user_has_perm(cashier, rbac.PERM_CASH_OPERATE)
    assert rbac.user_permissions(cashier) == [rbac.PERM_FINANCE_VIEW]


def test_role_without_db_rows_falls_back_to_default(chief):
    # Ни одной RolePermission в БД — работает DEFAULT_ROLE_PERMISSIONS.
    assert RolePermission.objects.count() == 0
    assert rbac.role_permissions(R.CHIEF_ACCOUNTANT) == frozenset(
        rbac.DEFAULT_ROLE_PERMISSIONS[R.CHIEF_ACCOUNTANT]
    )
    assert rbac.user_has_perm(chief, rbac.PERM_AUDIT_VIEW)


# --- Superuser / аноним / неактивный ---


def test_superuser_has_everything():
    su = f.UserFactory(role=R.MANAGER, is_superuser=True)
    assert rbac.user_has_perm(su, rbac.PERM_FINANCE_MANAGE)
    assert rbac.user_has_perm(su, rbac.PERM_OVERLAY_VIEW)
    assert rbac.user_has_perm(su, "какое-угодно.право")
    perms = rbac.user_permissions(su)
    assert rbac.PERM_OVERLAY_VIEW in perms
    assert rbac.PERM_FINANCE_MANAGE in perms


def test_anonymous_has_nothing():
    anon = AnonymousUser()
    assert not rbac.user_has_perm(anon, rbac.PERM_FINANCE_VIEW)
    assert not rbac.user_has_perm(None, rbac.PERM_FINANCE_VIEW)
    assert rbac.user_permissions(anon) == []
    assert list(rbac.accessible_businesses(anon)) == []


def test_inactive_user_has_nothing():
    user = f.ChiefFactory(is_active=False)
    assert not rbac.user_has_perm(user, rbac.PERM_FINANCE_VIEW)


# --- accessible_businesses ---


def test_view_all_roles_see_all_active_businesses():
    b1 = f.BusinessFactory()
    b2 = f.BusinessFactory()
    f.BusinessFactory(is_active=False)  # неактивный не виден никому
    for user in (f.OwnerFactory(), f.ChiefFactory()):
        ids = set(rbac.accessible_businesses(user).values_list("id", flat=True))
        assert ids == {b1.id, b2.id}


def test_cashier_sees_only_own_fk_and_business_access_rows():
    own = f.BusinessFactory()
    via_access = f.BusinessFactory()
    f.BusinessFactory()  # чужой бизнес
    cashier = f.CashierFactory(business=own)
    f.BusinessAccessFactory(user=cashier, business=via_access)
    ids = set(rbac.accessible_businesses(cashier).values_list("id", flat=True))
    assert ids == {own.id, via_access.id}


def test_adding_business_access_changes_transaction_visibility():
    business = f.BusinessFactory()
    tx = f.TransactionFactory(business=business, amount=Decimal("777.00"))
    cashier = f.CashierFactory()

    assert finance_selectors.transactions_for_user(cashier).count() == 0

    f.BusinessAccessFactory(user=cashier, business=business)
    visible = finance_selectors.transactions_for_user(cashier)
    assert list(visible.values_list("id", flat=True)) == [tx.id]
    assert visible.get().amount == Decimal("777.00")


# --- API бизнесов (Часть 0) ---


def test_owner_can_create_business(api, auth, owner_user):
    auth(api, owner_user)
    resp = api.post(
        "/api/v1/businesses/",
        {"name": "Новый завод", "code": "new-factory", "kind": "factory"},
        format="json",
    )
    assert resp.status_code == 201
    created = Business.objects.get(code="new-factory")
    assert created.name == "Новый завод"
    assert created.is_active is True
    assert resp.json()["kind_display"] == "Завод"


def test_owner_can_patch_business(api, auth, owner_user, business):
    auth(api, owner_user)
    resp = api.patch(
        f"/api/v1/businesses/{business.id}/", {"name": "Переименован"}, format="json"
    )
    assert resp.status_code == 200
    business.refresh_from_db()
    assert business.name == "Переименован"


def test_accountant_reads_but_cannot_mutate_businesses(api, auth, accountant, business):
    auth(api, accountant)
    resp = api.get("/api/v1/businesses/")
    assert resp.status_code == 200
    assert {row["id"] for row in resp.json()} == {business.id}

    resp = api.post(
        "/api/v1/businesses/",
        {"name": "Запрещено", "code": "denied", "kind": "other"},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "permission_denied"
    assert not Business.objects.filter(code="denied").exists()


def test_delete_business_deactivates_instead_of_removing(api, auth, owner_user, business):
    auth(api, owner_user)
    resp = api.delete(f"/api/v1/businesses/{business.id}/")
    assert resp.status_code == 204
    business.refresh_from_db()  # не удалён физически
    assert business.is_active is False


def test_businesses_endpoint_requires_auth(api):
    resp = api.get("/api/v1/businesses/")
    assert resp.status_code == 401
    assert resp.json()["code"] == "not_authenticated"
