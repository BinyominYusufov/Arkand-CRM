"""API-тесты /api/v1/payroll/runs/ (ЗРП-01, RBAC)."""
from datetime import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.finance.models import Transaction
from apps.payroll.models import PayrollRun, SalaryScheme
from apps.testing.factories import (
    BusinessFactory,
    EmployeeFactory,
    SalarySchemeFactory,
    TransactionFactory,
)

pytestmark = pytest.mark.django_db

RUNS_URL = "/api/v1/payroll/runs/"
YEAR, MONTH = 2026, 5


def finalize_url(run_id) -> str:
    return f"{RUNS_URL}{run_id}/finalize/"


def make_sales_employee(percent=10, base=3000, sales="25000.00"):
    business = BusinessFactory()
    emp = EmployeeFactory(business=business, is_salesperson=True)
    SalarySchemeFactory(
        employee=emp,
        scheme_type=SalaryScheme.SchemeType.PERCENT_OF_SALES,
        config={"base": base, "percent": percent},
    )
    TransactionFactory(
        business=business,
        kind=Transaction.Kind.INCOME,
        amount=Decimal(sales),
        status=Transaction.Status.CONFIRMED,
        occurred_at=timezone.make_aware(datetime(YEAR, MONTH, 15, 12)),
    )
    return emp


# --- создание расчёта ---


def test_create_run_returns_201_with_items(api, auth, accountant):
    emp = make_sales_employee()
    auth(api, accountant)

    resp = api.post(RUNS_URL, {"year": YEAR, "month": MONTH}, format="json")

    assert resp.status_code == 201
    data = resp.json()
    assert data["year"] == YEAR
    assert data["month"] == MONTH
    assert data["status"] == "draft"
    assert data["items_count"] == 1
    # total_fund не квантуется (Sum в SQLite -> "5500"), сравниваем значением
    assert Decimal(data["total_fund"]) == Decimal("5500.00")
    [item] = data["items"]
    assert item["employee"] == emp.pk
    # Деньги в API — строки
    assert item["base"] == "3000.00"
    assert item["bonus"] == "2500.00"
    assert item["total"] == "5500.00"
    assert item["breakdown"]["scheme_type"] == "percent_of_sales"
    assert item["breakdown"]["inputs"]["source"] == "auto"


def test_create_run_with_manual_inputs(api, auth, chief):
    emp = make_sales_employee()  # авто дало бы 2500 бонуса
    auth(api, chief)

    resp = api.post(
        RUNS_URL,
        {
            "year": YEAR,
            "month": MONTH,
            "inputs": {str(emp.pk): {"sales_amount": "1000", "units": 0}},
        },
        format="json",
    )

    assert resp.status_code == 201
    [item] = resp.json()["items"]
    assert item["bonus"] == "100.00"
    assert item["breakdown"]["inputs"]["source"] == "manual"


def test_create_run_twice_reuses_draft_unique_period(api, auth, accountant):
    make_sales_employee()
    auth(api, accountant)

    first = api.post(RUNS_URL, {"year": YEAR, "month": MONTH}, format="json")
    second = api.post(RUNS_URL, {"year": YEAR, "month": MONTH}, format="json")

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert PayrollRun.objects.count() == 1  # unique (year, month)
    assert second.json()["items_count"] == 1


def test_create_run_validation_error(api, auth, accountant):
    auth(api, accountant)
    resp = api.post(RUNS_URL, {"year": YEAR, "month": 13}, format="json")
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "validation_error"
    assert set(body) == {"code", "message", "details"}


# --- finalize ---


def test_finalize_run(api, auth, accountant):
    make_sales_employee()
    auth(api, accountant)
    run_id = api.post(
        RUNS_URL, {"year": YEAR, "month": MONTH}, format="json"
    ).json()["id"]

    resp = api.post(finalize_url(run_id))

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "finalized"
    assert data["finalized_at"] is not None


def test_finalize_twice_conflict_409(api, auth, accountant):
    auth(api, accountant)
    run_id = api.post(
        RUNS_URL, {"year": YEAR, "month": MONTH}, format="json"
    ).json()["id"]
    api.post(finalize_url(run_id))

    resp = api.post(finalize_url(run_id))

    assert resp.status_code == 409
    body = resp.json()
    assert body["code"] == "conflict"
    assert set(body) == {"code", "message", "details"}


def test_create_run_for_finalized_period_409(api, auth, accountant):
    auth(api, accountant)
    run_id = api.post(
        RUNS_URL, {"year": YEAR, "month": MONTH}, format="json"
    ).json()["id"]
    api.post(finalize_url(run_id))

    resp = api.post(RUNS_URL, {"year": YEAR, "month": MONTH}, format="json")

    assert resp.status_code == 409
    assert resp.json()["code"] == "conflict"


# --- чтение ---


def test_retrieve_run_detail_has_items(api, auth, accountant):
    make_sales_employee()
    auth(api, accountant)
    run_id = api.post(
        RUNS_URL, {"year": YEAR, "month": MONTH}, format="json"
    ).json()["id"]

    resp = api.get(f"{RUNS_URL}{run_id}/")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert "breakdown" in data["items"][0]


def test_list_runs(api, auth, accountant):
    auth(api, accountant)
    api.post(RUNS_URL, {"year": YEAR, "month": MONTH}, format="json")

    resp = api.get(RUNS_URL)

    assert resp.status_code == 200
    payload = resp.json()
    rows = payload["results"] if isinstance(payload, dict) else payload
    assert len(rows) == 1
    assert rows[0]["year"] == YEAR


# --- права (RBAC) ---


def test_cashier_forbidden(api, auth, cashier):
    auth(api, cashier)
    assert api.get(RUNS_URL).status_code == 403
    resp = api.post(RUNS_URL, {"year": YEAR, "month": MONTH}, format="json")
    assert resp.status_code == 403
    assert resp.json()["code"] == "permission_denied"
    assert PayrollRun.objects.count() == 0


def test_owner_can_read_but_not_run(api, auth, owner_user, accountant):
    auth(api, accountant)
    run_id = api.post(
        RUNS_URL, {"year": YEAR, "month": MONTH}, format="json"
    ).json()["id"]

    auth(api, owner_user)
    assert api.get(RUNS_URL).status_code == 200
    assert api.get(f"{RUNS_URL}{run_id}/").status_code == 200
    assert (
        api.post(RUNS_URL, {"year": YEAR, "month": 6}, format="json").status_code
        == 403
    )
    assert api.post(finalize_url(run_id)).status_code == 403


def test_anonymous_unauthorized(api):
    resp = api.get(RUNS_URL)
    assert resp.status_code == 401
    assert resp.json()["code"] == "not_authenticated"
