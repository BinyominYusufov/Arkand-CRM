"""Тесты селекторов финансов: видимость операций и прибыль (ФНС-03, ФНС-04)."""
from datetime import date, datetime, timezone as dt_tz
from decimal import Decimal

import pytest

from apps.finance import selectors
from apps.finance.models import Transaction
from apps.testing import factories as f

pytestmark = pytest.mark.django_db


def _dt(year, month, day, hour=12):
    """Aware-datetime в UTC; 12:00 UTC == 17:00 Asia/Dushanbe — та же дата."""
    return datetime(year, month, day, hour, 0, tzinfo=dt_tz.utc)


def _confirmed_income(business, amount, occurred_at=None, **kw):
    return f.TransactionFactory(
        business=business,
        kind=Transaction.Kind.INCOME,
        status=Transaction.Status.CONFIRMED,
        amount=Decimal(amount),
        occurred_at=occurred_at or _dt(2026, 3, 10),
        **kw,
    )


def _confirmed_expense(business, amount, occurred_at=None, **kw):
    return f.TransactionFactory(
        business=business,
        kind=Transaction.Kind.EXPENSE,
        category=f.ExpenseCategoryFactory(),
        status=Transaction.Status.CONFIRMED,
        amount=Decimal(amount),
        occurred_at=occurred_at or _dt(2026, 3, 15),
        **kw,
    )


# ---------- transactions_for_user ----------


def test_finance_roles_see_all_alive_transactions(accountant, business):
    other = f.BusinessFactory()
    visible1 = f.TransactionFactory(business=business)
    visible2 = f.TransactionFactory(business=other)
    hidden = f.TransactionFactory(business=business, is_deleted=True)

    ids = set(selectors.transactions_for_user(accountant).values_list("id", flat=True))
    assert visible1.id in ids
    assert visible2.id in ids
    assert hidden.id not in ids


def test_user_without_access_sees_nothing(cashier, business):
    f.TransactionFactory(business=business)
    assert selectors.transactions_for_user(cashier).count() == 0


def test_business_access_limits_queryset(cashier, business):
    other = f.BusinessFactory()
    mine = f.TransactionFactory(business=business)
    alien = f.TransactionFactory(business=other)
    f.BusinessAccessFactory(user=cashier, business=business)

    ids = set(selectors.transactions_for_user(cashier).values_list("id", flat=True))
    assert ids == {mine.id}
    assert alien.id not in ids


# ---------- profit_for_business (ФНС-04) ----------


@pytest.fixture
def profit_data(business):
    """Доходы/расходы бизнеса + шум, который не должен учитываться."""
    _confirmed_income(business, "1000.00", _dt(2026, 3, 10))
    _confirmed_income(business, "500.00", _dt(2026, 3, 20))
    _confirmed_expense(business, "300.00", _dt(2026, 3, 15))
    # Шум: pending, void, soft-deleted, чужой бизнес.
    f.TransactionFactory(
        business=business,
        status=Transaction.Status.PENDING,
        amount=Decimal("999.00"),
        occurred_at=_dt(2026, 3, 11),
    )
    f.TransactionFactory(
        business=business,
        kind=Transaction.Kind.EXPENSE,
        category=f.ExpenseCategoryFactory(),
        status=Transaction.Status.VOID,
        amount=Decimal("888.00"),
        occurred_at=_dt(2026, 3, 11),
    )
    _confirmed_income(business, "777.00", _dt(2026, 3, 11), is_deleted=True)
    _confirmed_income(f.BusinessFactory(), "5555.00", _dt(2026, 3, 11))
    return business


def test_profit_for_business_counts_only_confirmed_alive(profit_data):
    business = profit_data
    result = selectors.profit_for_business(business)
    assert result["business_id"] == business.id
    assert result["business_name"] == business.name
    assert result["income"] == Decimal("1500.00")
    assert result["expense"] == Decimal("300.00")
    assert result["profit"] == Decimal("1200.00")


def test_profit_for_business_date_from(profit_data):
    result = selectors.profit_for_business(profit_data, date_from=date(2026, 3, 12))
    assert result["income"] == Decimal("500.00")
    assert result["expense"] == Decimal("300.00")
    assert result["profit"] == Decimal("200.00")


def test_profit_for_business_date_to(profit_data):
    result = selectors.profit_for_business(profit_data, date_to=date(2026, 3, 12))
    assert result["income"] == Decimal("1000.00")
    assert result["expense"] == Decimal("0.00")
    assert result["profit"] == Decimal("1000.00")


def test_profit_for_business_period_can_be_negative(profit_data):
    result = selectors.profit_for_business(
        profit_data, date_from=date(2026, 3, 12), date_to=date(2026, 3, 16)
    )
    assert result["income"] == Decimal("0.00")
    assert result["expense"] == Decimal("300.00")
    assert result["profit"] == Decimal("-300.00")


def test_profit_for_business_boundary_dates_inclusive(business):
    _confirmed_income(business, "100.00", _dt(2026, 5, 1))
    _confirmed_income(business, "200.00", _dt(2026, 5, 31))
    result = selectors.profit_for_business(
        business, date_from=date(2026, 5, 1), date_to=date(2026, 5, 31)
    )
    assert result["income"] == Decimal("300.00")


def test_profit_empty_business_is_zero(business):
    result = selectors.profit_for_business(business)
    assert result["income"] == Decimal("0.00")
    assert result["expense"] == Decimal("0.00")
    assert result["profit"] == Decimal("0.00")


# ---------- profit_by_business ----------


def test_profit_by_business_rows_and_total():
    b1 = f.BusinessFactory()
    b2 = f.BusinessFactory()
    _confirmed_income(b1, "1000.00")
    _confirmed_expense(b1, "400.00")
    _confirmed_income(b2, "250.00")

    data = selectors.profit_by_business()
    rows = {r["business_id"]: r for r in data["businesses"]}
    assert rows[b1.id]["profit"] == Decimal("600.00")
    assert rows[b2.id]["income"] == Decimal("250.00")
    assert rows[b2.id]["expense"] == Decimal("0.00")
    assert data["total"] == {
        "income": Decimal("1250.00"),
        "expense": Decimal("400.00"),
        "profit": Decimal("850.00"),
    }


def test_profit_by_business_default_skips_inactive():
    active = f.BusinessFactory()
    inactive = f.BusinessFactory(is_active=False)
    _confirmed_income(active, "10.00")
    _confirmed_income(inactive, "9999.00")

    data = selectors.profit_by_business()
    ids = {r["business_id"] for r in data["businesses"]}
    assert active.id in ids
    assert inactive.id not in ids
    assert data["total"]["income"] == Decimal("10.00")


def test_profit_by_business_explicit_businesses_and_dates():
    b1 = f.BusinessFactory()
    b2 = f.BusinessFactory()
    _confirmed_income(b1, "100.00", _dt(2026, 1, 10))
    _confirmed_income(b1, "50.00", _dt(2026, 2, 10))
    _confirmed_income(b2, "70.00", _dt(2026, 1, 10))

    data = selectors.profit_by_business(
        date_from=date(2026, 1, 1), date_to=date(2026, 1, 31), businesses=[b1]
    )
    assert [r["business_id"] for r in data["businesses"]] == [b1.id]
    assert data["total"] == {
        "income": Decimal("100.00"),
        "expense": Decimal("0.00"),
        "profit": Decimal("100.00"),
    }
