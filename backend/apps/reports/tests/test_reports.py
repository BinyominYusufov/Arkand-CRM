"""Отчёты ФНС-10…13 на контролируемых данных: точные суммы, строки-деньги, права."""
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.cash.models import CashRegister
from apps.finance.models import Transaction
from apps.payroll.models import PayrollItem
from apps.settlements.models import Debt, DebtSettlement
from apps.testing import factories as f

pytestmark = pytest.mark.django_db

D = Decimal


def assert_money(value, expected):
    """Деньги в API — строкой; значение сравниваем как Decimal.

    Точную строку не фиксируем: агрегаты Sum() на SQLite дают '1000',
    а значения полей — '1000.00' (см. bugs_found: формат не нормализован).
    """
    assert isinstance(value, str)
    assert D(value) == D(expected)


def confirmed_tx(business, kind, amount, category=None):
    return f.TransactionFactory(
        business=business,
        kind=kind,
        amount=D(amount),
        category=category,
        status=Transaction.Status.CONFIRMED,
    )


@pytest.fixture
def two_businesses(db, category):
    """b1: доход 1000, расход 400; b2: доход 2000, расход 500 (только confirmed)."""
    b1 = f.BusinessFactory()
    b2 = f.BusinessFactory()
    confirmed_tx(b1, Transaction.Kind.INCOME, "1000.00")
    confirmed_tx(b1, Transaction.Kind.EXPENSE, "400.00", category=category)
    confirmed_tx(b2, Transaction.Kind.INCOME, "2000.00")
    confirmed_tx(b2, Transaction.Kind.EXPENSE, "500.00", category=category)
    # Шум, который НЕ должен попасть в отчёты:
    f.TransactionFactory(business=b1, amount=D("600.00"), status=Transaction.Status.PENDING)
    f.TransactionFactory(business=b1, amount=D("250.00"), status=Transaction.Status.VOID)
    f.TransactionFactory(
        business=b2,
        amount=D("999.00"),
        status=Transaction.Status.CONFIRMED,
        is_deleted=True,
    )
    return b1, b2


# --- ФНС-10: cashflow ---


def test_cashflow_report_exact_sums_and_strings(api, auth, chief, two_businesses):
    b1, b2 = two_businesses
    auth(api, chief)
    resp = api.get("/api/v1/reports/cashflow")
    assert resp.status_code == 200
    data = resp.json()

    rows = {r["business_id"]: r for r in data["businesses"]}
    assert set(rows) == {b1.id, b2.id}
    assert_money(rows[b1.id]["income"], "1000.00")
    assert_money(rows[b1.id]["expense"], "400.00")
    assert_money(rows[b1.id]["profit"], "600.00")
    assert_money(rows[b2.id]["income"], "2000.00")
    assert_money(rows[b2.id]["expense"], "500.00")
    assert_money(rows[b2.id]["profit"], "1500.00")

    assert_money(data["total"]["income"], "3000.00")
    assert_money(data["total"]["expense"], "900.00")
    assert_money(data["total"]["profit"], "2100.00")
    # total сходится с построчной суммой.
    for key in ("income", "expense", "profit"):
        assert D(data["total"][key]) == sum(
            (D(r[key]) for r in data["businesses"]), D("0")
        )


def test_cashflow_monthly_rows_per_month_and_business(api, auth, chief, two_businesses):
    b1, b2 = two_businesses
    auth(api, chief)
    resp = api.get("/api/v1/reports/cashflow/monthly", {"months": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["months"] == 3

    current_month = timezone.localtime().strftime("%Y-%m")
    rows = {(r["month"], r["business_id"]): r for r in data["rows"]}
    assert set(rows) == {(current_month, b1.id), (current_month, b2.id)}

    r1 = rows[(current_month, b1.id)]
    assert_money(r1["income"], "1000.00")
    assert_money(r1["expense"], "400.00")
    assert r1["business_name"] == b1.name
    r2 = rows[(current_month, b2.id)]
    assert_money(r2["income"], "2000.00")
    assert_money(r2["expense"], "500.00")


# --- ФНС-11: cash-registers ---


def test_cash_registers_report_balance_turnover_over_limit(api, auth, chief):
    business = f.BusinessFactory()
    r1 = f.CashRegisterFactory(business=business, turnover_limit=D("50000.00"))
    f.CashOperationFactory(register=r1, direction="in", amount=D("1000.00"))
    f.CashOperationFactory(register=r1, direction="out", amount=D("300.00"))
    # Удалённая операция не считается.
    f.CashOperationFactory(register=r1, direction="in", amount=D("111.00"), is_deleted=True)

    r2 = f.CashRegisterFactory(business=business, turnover_limit=D("10000.00"))
    f.CashOperationFactory(register=r2, direction="in", amount=D("400.00"))
    # Снижаем лимит уже ПОСЛЕ операций — касса становится over_limit.
    CashRegister.objects.filter(pk=r2.pk).update(turnover_limit=D("100.00"))

    auth(api, chief)
    resp = api.get("/api/v1/reports/cash-registers")
    assert resp.status_code == 200
    data = resp.json()

    rows = {r["id"]: r for r in data["registers"]}
    assert set(rows) == {r1.id, r2.id}

    assert_money(rows[r1.id]["balance"], "700.00")  # 1000 - 300
    assert_money(rows[r1.id]["month_turnover"], "1300.00")  # 1000 + 300
    assert_money(rows[r1.id]["turnover_limit"], "50000.00")
    assert rows[r1.id]["over_limit"] is False

    assert_money(rows[r2.id]["balance"], "400.00")
    assert_money(rows[r2.id]["month_turnover"], "400.00")
    assert_money(rows[r2.id]["turnover_limit"], "100.00")
    assert rows[r2.id]["over_limit"] is True
    assert rows[r2.id]["limit_utilization"] == pytest.approx(400.0)

    assert_money(data["total_balance"], "1100.00")
    assert_money(data["total_month_turnover"], "1700.00")


# --- ФНС-12: debts ---


def test_debts_report_total_open_equals_sum_of_remaining(api, auth, accountant):
    b1, b2, b3 = f.BusinessFactory(), f.BusinessFactory(), f.BusinessFactory()
    d1 = f.DebtFactory(debtor=b1, creditor=b2, amount=D("5000.00"))
    d2 = f.DebtFactory(debtor=b1, creditor=b2, amount=D("3000.00"))
    DebtSettlement.objects.create(debt=d2, method="return", amount=D("1000.00"))
    # Закрытый долг и полностью погашенный открытый — вне реестра.
    f.DebtFactory(debtor=b2, creditor=b3, amount=D("700.00"), status=Debt.Status.CLOSED)
    settled = f.DebtFactory(debtor=b3, creditor=b1, amount=D("200.00"))
    DebtSettlement.objects.create(debt=settled, method="offset", amount=D("200.00"))

    auth(api, accountant)
    resp = api.get("/api/v1/reports/debts")
    assert resp.status_code == 200
    data = resp.json()

    rows = {r["id"]: r for r in data["debts"]}
    assert set(rows) == {d1.id, d2.id}
    assert rows[d1.id]["remaining"] == "5000.00"
    assert rows[d2.id]["amount"] == "3000.00"
    assert rows[d2.id]["remaining"] == "2000.00"
    assert rows[d1.id]["debtor_id"] == b1.id
    assert rows[d1.id]["creditor_id"] == b2.id

    assert data["total_open"] == "7000.00"
    assert D(data["total_open"]) == sum((D(r["remaining"]) for r in data["debts"]), D("0"))

    assert len(data["pairs"]) == 1
    pair = data["pairs"][0]
    assert pair["debtor_id"] == b1.id
    assert pair["creditor_id"] == b2.id
    assert pair["total_remaining"] == "7000.00"
    assert pair["debts_count"] == 2


# --- ФНС-13: payroll ---


def test_payroll_report_fund_matches_payroll_items(api, auth, chief):
    b1 = f.BusinessFactory()
    b2 = f.BusinessFactory()
    run = f.PayrollRunFactory(year=2026, month=6)
    e1 = f.EmployeeFactory(business=b1)
    e2 = f.EmployeeFactory(business=b2)
    e3 = f.EmployeeFactory(business=None)  # головной офис
    PayrollItem.objects.create(
        run=run, employee=e1, base=D("3000.00"), bonus=D("500.00"), total=D("3500.00")
    )
    PayrollItem.objects.create(
        run=run, employee=e2, base=D("2000.00"), bonus=D("0.00"), total=D("2000.00")
    )
    PayrollItem.objects.create(
        run=run, employee=e3, base=D("1000.00"), bonus=D("0.00"), total=D("1000.00")
    )

    auth(api, chief)
    resp = api.get("/api/v1/reports/payroll", {"year": 2026, "month": 6})
    assert resp.status_code == 200
    data = resp.json()

    assert data["period"] == {"year": 2026, "month": 6, "status": "draft"}
    assert_money(data["fund_total"], "6500.00")

    rows = {r["business_id"]: r for r in data["fund_by_business"]}
    assert set(rows) == {b1.id, b2.id, None}
    assert_money(rows[b1.id]["base"], "3000.00")
    assert_money(rows[b1.id]["bonus"], "500.00")
    assert_money(rows[b1.id]["fund"], "3500.00")
    assert_money(rows[b2.id]["fund"], "2000.00")
    assert rows[None]["business_name"] == "Головной офис"
    assert_money(rows[None]["fund"], "1000.00")

    # fund_total сходится с построчной суммой.
    assert D(data["fund_total"]) == sum(
        (D(r["fund"]) for r in data["fund_by_business"]), D("0")
    )

    run_row = next(r for r in data["runs"] if r["id"] == run.pk)
    assert_money(run_row["fund"], "6500.00")
    assert run_row["status"] == "draft"


# --- Права на отчёты ---

REPORT_PATHS = [
    "/api/v1/reports/cashflow",
    "/api/v1/reports/cashflow/monthly",
    "/api/v1/reports/expenses/by-category",
    "/api/v1/reports/cash-registers",
    "/api/v1/reports/debts",
    "/api/v1/reports/payroll",
]


@pytest.mark.parametrize("path", REPORT_PATHS)
def test_cashier_gets_403_on_every_report(api, auth, cashier, path):
    auth(api, cashier)
    resp = api.get(path)
    assert resp.status_code == 403
    assert resp.json()["code"] == "permission_denied"


@pytest.mark.parametrize("path", REPORT_PATHS)
def test_owner_gets_200_on_every_report(api, auth, owner_user, path):
    auth(api, owner_user)
    assert api.get(path).status_code == 200
