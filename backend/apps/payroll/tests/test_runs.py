"""Сервисные тесты run_payroll / finalize_run (ЗРП-01) — с БД."""
from datetime import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.exceptions import ConflictError
from apps.finance.models import Transaction
from apps.payroll.models import PayrollRun, SalaryScheme
from apps.payroll.services import finalize_run, run_payroll
from apps.testing.factories import (
    BusinessFactory,
    EmployeeFactory,
    SalarySchemeFactory,
    TransactionFactory,
)

pytestmark = pytest.mark.django_db

YEAR, MONTH = 2026, 5


def _dt(day: int, hour: int = 12):
    return timezone.make_aware(datetime(YEAR, MONTH, day, hour))


def confirmed_income(business, amount, day=15):
    return TransactionFactory(
        business=business,
        kind=Transaction.Kind.INCOME,
        amount=Decimal(str(amount)),
        status=Transaction.Status.CONFIRMED,
        occurred_at=_dt(day),
    )


# --- авто-inputs ---


def test_run_payroll_auto_sales_for_percent_scheme(accountant):
    business = BusinessFactory()
    emp = EmployeeFactory(business=business, is_salesperson=True)
    SalarySchemeFactory(
        employee=emp,
        scheme_type=SalaryScheme.SchemeType.PERCENT_OF_SALES,
        config={"base": 3000, "percent": 10},
    )
    confirmed_income(business, "10000.00", day=5)
    confirmed_income(business, "15000.00", day=20)
    # Шум: pending, void и чужой бизнес не попадают в auto-inputs
    TransactionFactory(business=business, amount=Decimal("777.00"),
                       status=Transaction.Status.PENDING, occurred_at=_dt(10))
    TransactionFactory(business=business, amount=Decimal("888.00"),
                       status=Transaction.Status.VOID, occurred_at=_dt(10))
    confirmed_income(BusinessFactory(), "5000.00")

    run = run_payroll(accountant, year=YEAR, month=MONTH)

    assert run.status == PayrollRun.Status.DRAFT
    assert run.created_by == accountant
    item = run.items.get(employee=emp)
    assert item.base == Decimal("3000.00")
    assert item.bonus == Decimal("2500.00")  # 25000 * 10%
    assert item.total == Decimal("5500.00")
    # Строка не квантуется селектором Sum (SQLite: "25000"), сравниваем значением
    assert Decimal(item.breakdown["inputs"]["sales_amount"]) == Decimal("25000.00")
    assert item.breakdown["inputs"]["source"] == "auto"


def test_run_payroll_auto_units_for_per_unit_scheme(accountant):
    business = BusinessFactory()
    emp = EmployeeFactory(business=business)
    SalarySchemeFactory(
        employee=emp,
        scheme_type=SalaryScheme.SchemeType.PER_UNIT_TIERED,
        config={
            "base": 1000,
            "tier_mode": "marginal",
            "tiers": [{"upto": 2, "rate": 500}, {"upto": None, "rate": 1000}],
        },
    )
    for day in (3, 10, 21):  # 3 подтверждённых прихода -> units=3
        confirmed_income(business, "100.00", day=day)

    run = run_payroll(accountant, year=YEAR, month=MONTH)

    item = run.items.get(employee=emp)
    assert item.breakdown["inputs"]["units"] == 3
    assert item.bonus == Decimal("2000.00")  # 2*500 + 1*1000
    assert item.total == Decimal("3000.00")


def test_run_payroll_employee_without_business_gets_zero_inputs(accountant):
    emp = EmployeeFactory(business=None, salary_type="administrative")
    SalarySchemeFactory(
        employee=emp,
        scheme_type=SalaryScheme.SchemeType.FIXED,
        config={"base": 4000},
    )
    run = run_payroll(accountant, year=YEAR, month=MONTH)
    item = run.items.get(employee=emp)
    assert item.total == Decimal("4000.00")
    assert item.breakdown["inputs"]["source"] == "none"


# --- ручные inputs перекрывают авто ---


def test_run_payroll_manual_inputs_override_auto(accountant):
    business = BusinessFactory()
    emp = EmployeeFactory(business=business, is_salesperson=True)
    SalarySchemeFactory(
        employee=emp,
        scheme_type=SalaryScheme.SchemeType.PERCENT_OF_SALES,
        config={"base": 0, "percent": 10},
    )
    confirmed_income(business, "25000.00")  # авто дало бы бонус 2500

    run = run_payroll(
        accountant,
        year=YEAR,
        month=MONTH,
        inputs={emp.pk: {"sales_amount": "1000", "units": 0}},
    )

    item = run.items.get(employee=emp)
    assert item.bonus == Decimal("100.00")  # 1000 * 10%, не 2500
    assert item.breakdown["inputs"]["sales_amount"] == "1000"
    assert item.breakdown["inputs"]["source"] == "manual"


def test_run_payroll_manual_inputs_string_keys(accountant):
    emp = EmployeeFactory()
    SalarySchemeFactory(
        employee=emp,
        scheme_type=SalaryScheme.SchemeType.PER_UNIT_TIERED,
        config={"base": 0, "tier_mode": "flat",
                "tiers": [{"upto": None, "rate": 200}]},
    )
    run = run_payroll(
        accountant, year=YEAR, month=MONTH,
        inputs={str(emp.pk): {"units": 4}},
    )
    item = run.items.get(employee=emp)
    assert item.bonus == Decimal("800.00")
    assert item.breakdown["inputs"]["source"] == "manual"


# --- пропуски и пересчёт ---


def test_run_payroll_skips_employee_without_active_scheme(accountant):
    with_scheme = EmployeeFactory()
    SalarySchemeFactory(employee=with_scheme, config={"base": 1000})
    no_scheme = EmployeeFactory()
    inactive_scheme = EmployeeFactory()
    SalarySchemeFactory(employee=inactive_scheme, is_active=False)
    inactive_emp = EmployeeFactory(is_active=False)
    SalarySchemeFactory(employee=inactive_emp)

    run = run_payroll(accountant, year=YEAR, month=MONTH)

    assert run.items.count() == 1
    assert run.items.get().employee == with_scheme
    assert not run.items.filter(employee=no_scheme).exists()


def test_run_payroll_draft_recalculates_without_duplicates(accountant):
    business = BusinessFactory()
    emp = EmployeeFactory(business=business, is_salesperson=True)
    SalarySchemeFactory(
        employee=emp,
        scheme_type=SalaryScheme.SchemeType.PERCENT_OF_SALES,
        config={"base": 0, "percent": 10},
    )
    confirmed_income(business, "10000.00")

    run1 = run_payroll(accountant, year=YEAR, month=MONTH)
    assert run1.items.get().bonus == Decimal("1000.00")

    confirmed_income(business, "5000.00")  # новые продажи -> пересчёт
    run2 = run_payroll(accountant, year=YEAR, month=MONTH)

    assert run2.pk == run1.pk  # тот же run, unique (year, month)
    assert PayrollRun.objects.count() == 1
    assert run2.items.count() == 1  # items заменены, не задублированы
    assert run2.items.get().bonus == Decimal("1500.00")


def test_run_payroll_finalized_raises_conflict(accountant, chief):
    emp = EmployeeFactory()
    SalarySchemeFactory(employee=emp)
    run = run_payroll(accountant, year=YEAR, month=MONTH)
    finalize_run(chief, run_id=run.pk)

    with pytest.raises(ConflictError):
        run_payroll(accountant, year=YEAR, month=MONTH)
    assert run.items.count() == 1  # строки утверждённого не тронуты


# --- finalize_run ---


def test_finalize_run_sets_status_and_timestamp(accountant, chief):
    emp = EmployeeFactory()
    SalarySchemeFactory(employee=emp)
    run = run_payroll(accountant, year=YEAR, month=MONTH)
    assert run.finalized_at is None

    result = finalize_run(chief, run_id=run.pk)

    assert result.status == PayrollRun.Status.FINALIZED
    assert result.finalized_at is not None
    run.refresh_from_db()
    assert run.status == PayrollRun.Status.FINALIZED


def test_finalize_run_twice_raises_conflict(accountant):
    run = run_payroll(accountant, year=YEAR, month=MONTH)
    finalize_run(accountant, run_id=run.pk)
    with pytest.raises(ConflictError):
        finalize_run(accountant, run_id=run.pk)


def test_finalize_missing_run_raises_conflict(accountant):
    with pytest.raises(ConflictError):
        finalize_run(accountant, run_id=999999)


# --- AuditLog ---


def test_audit_log_on_run_calculated(accountant):
    emp = EmployeeFactory()
    SalarySchemeFactory(employee=emp, config={"base": 3000})
    run = run_payroll(accountant, year=YEAR, month=MONTH)

    log = AuditLog.objects.get(action="payroll.run_calculated")
    assert log.actor == accountant
    assert log.entity_type == "PayrollRun"
    assert log.entity_id == str(run.pk)
    assert log.after["items"] == 1
    assert log.after["fund"] == "3000.00"
    assert log.after["year"] == YEAR
    assert log.after["month"] == MONTH


def test_audit_log_on_run_finalized(accountant, chief):
    run = run_payroll(accountant, year=YEAR, month=MONTH)
    finalize_run(chief, run_id=run.pk)

    log = AuditLog.objects.get(action="payroll.run_finalized")
    assert log.actor == chief
    assert log.entity_id == str(run.pk)
    assert log.before == {"status": "draft"}
    assert log.after == {"status": "finalized"}
