"""Общие фикстуры pytest для всего backend."""
import pytest
from rest_framework.test import APIClient

from apps.testing import factories as f


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def chief(db):
    return f.ChiefFactory()


@pytest.fixture
def accountant(db):
    return f.AccountantFactory()


@pytest.fixture
def cashier(db):
    return f.CashierFactory()


@pytest.fixture
def owner_user(db):
    return f.OwnerFactory()


@pytest.fixture
def business(db):
    return f.BusinessFactory()


@pytest.fixture
def category(db):
    return f.ExpenseCategoryFactory()


def as_user(api: APIClient, user) -> APIClient:
    """Аутентификация в API-тестах (JWT-поток тестируется отдельно)."""
    api.force_authenticate(user=user)
    return api


@pytest.fixture
def auth():
    return as_user
