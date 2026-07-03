"""Юнит-тесты движка зарплаты calculate_item (ЗРП-03…05) — без БД.

Схемы строятся через SalarySchemeFactory.build(employee=None):
calculate_item читает только scheme_type и config.
"""
from decimal import Decimal

import pytest

from apps.core.exceptions import DomainError
from apps.payroll.models import SalaryScheme
from apps.payroll.services import calculate_item
from apps.testing.factories import SalarySchemeFactory


def make_scheme(scheme_type, config):
    return SalarySchemeFactory.build(
        employee=None, scheme_type=scheme_type, config=config
    )


# --- fixed (ЗРП-03) ---


def test_fixed_base_only():
    scheme = make_scheme(SalaryScheme.SchemeType.FIXED, {"base": 3000})
    base, bonus, breakdown = calculate_item(scheme)
    assert base == Decimal("3000.00")
    assert bonus == Decimal("0.00")
    assert isinstance(base, Decimal)
    assert isinstance(bonus, Decimal)
    assert breakdown["scheme_type"] == "fixed"
    assert breakdown["base"] == "3000.00"
    assert breakdown["total"] == "3000.00"
    assert breakdown["bonus"] == "0.00"


def test_fixed_ignores_sales_and_units():
    scheme = make_scheme(SalaryScheme.SchemeType.FIXED, {"base": 1500})
    base, bonus, _ = calculate_item(
        scheme, sales_amount=Decimal("99999.99"), units=42
    )
    assert (base, bonus) == (Decimal("1500.00"), Decimal("0.00"))


# --- percent_of_sales (ЗРП-04) ---


def test_percent_of_sales_bonus():
    scheme = make_scheme(
        SalaryScheme.SchemeType.PERCENT_OF_SALES, {"base": 3000, "percent": 10}
    )
    base, bonus, breakdown = calculate_item(scheme, sales_amount=Decimal("25000"))
    assert base == Decimal("3000.00")
    assert bonus == Decimal("2500.00")
    assert breakdown["percent"] == "10"
    assert breakdown["inputs"]["sales_amount"] == "25000"
    assert breakdown["total"] == "5500.00"


def test_percent_of_sales_zero_sales():
    scheme = make_scheme(
        SalaryScheme.SchemeType.PERCENT_OF_SALES, {"base": 3000, "percent": 10}
    )
    _, bonus, _ = calculate_item(scheme, sales_amount=Decimal("0"))
    assert bonus == Decimal("0.00")


def test_percent_rounding_two_places():
    # 333.33 * 10% = 33.333 -> 33.33
    scheme = make_scheme(
        SalaryScheme.SchemeType.PERCENT_OF_SALES, {"base": 0, "percent": 10}
    )
    _, bonus, _ = calculate_item(scheme, sales_amount=Decimal("333.33"))
    assert bonus == Decimal("33.33")


def test_percent_rounding_half_up():
    # 100.05 * 10% = 10.005 -> ROUND_HALF_UP -> 10.01 (banker's дало бы 10.00)
    scheme = make_scheme(
        SalaryScheme.SchemeType.PERCENT_OF_SALES, {"base": 0, "percent": 10}
    )
    _, bonus, _ = calculate_item(scheme, sales_amount=Decimal("100.05"))
    assert bonus == Decimal("10.01")
    assert isinstance(bonus, Decimal)


# --- per_unit_tiered flat (ЗРП-05) ---

FLAT_CONFIG = {
    "base": 0,
    "unit": "квартира",
    "tier_mode": "flat",
    "tiers": [{"upto": 10, "rate": 500}, {"upto": None, "rate": 1000}],
}


@pytest.mark.parametrize(
    "units,expected",
    [
        (0, Decimal("0.00")),
        (10, Decimal("5000.00")),
        (11, Decimal("11000.00")),  # flat: ВСЯ сумма по достигнутой ставке
    ],
)
def test_per_unit_flat(units, expected):
    scheme = make_scheme(SalaryScheme.SchemeType.PER_UNIT_TIERED, FLAT_CONFIG)
    _, bonus, breakdown = calculate_item(scheme, units=units)
    assert bonus == expected
    assert breakdown["tier_mode"] == "flat"
    assert breakdown["unit"] == "квартира"
    assert breakdown["tiers_applied"] == [
        {
            "units": units,
            "rate": "500" if units <= 10 else "1000",
            "amount": str(expected),
        }
    ]


# --- per_unit_tiered marginal (ЗРП-05) ---

MARGINAL_CONFIG = {
    "base": 0,
    "tier_mode": "marginal",
    "tiers": [{"upto": 10, "rate": 500}, {"upto": None, "rate": 1000}],
}


@pytest.mark.parametrize(
    "units,expected",
    [
        (0, Decimal("0.00")),
        (10, Decimal("5000.00")),
        (11, Decimal("6000.00")),  # 10*500 + 1*1000
        (25, Decimal("20000.00")),  # 10*500 + 15*1000
    ],
)
def test_per_unit_marginal(units, expected):
    scheme = make_scheme(SalaryScheme.SchemeType.PER_UNIT_TIERED, MARGINAL_CONFIG)
    _, bonus, breakdown = calculate_item(scheme, units=units)
    assert bonus == expected
    assert breakdown["tier_mode"] == "marginal"


def test_per_unit_marginal_breakdown_bands():
    scheme = make_scheme(SalaryScheme.SchemeType.PER_UNIT_TIERED, MARGINAL_CONFIG)
    _, _, breakdown = calculate_item(scheme, units=11)
    assert breakdown["tiers_applied"] == [
        {"units": 10, "rate": "500", "amount": "5000.00"},
        {"units": 1, "rate": "1000", "amount": "1000.00"},
    ]


def test_per_unit_base_plus_bonus_total():
    config = dict(MARGINAL_CONFIG, base=3000)
    scheme = make_scheme(SalaryScheme.SchemeType.PER_UNIT_TIERED, config)
    base, bonus, breakdown = calculate_item(scheme, units=11)
    assert base == Decimal("3000.00")
    assert bonus == Decimal("6000.00")
    assert breakdown["total"] == "9000.00"


# --- невалидные схемы ---


@pytest.mark.parametrize("tiers", [[], None])
def test_per_unit_empty_tiers_raises(tiers):
    scheme = make_scheme(
        SalaryScheme.SchemeType.PER_UNIT_TIERED,
        {"base": 0, "tier_mode": "flat", "tiers": tiers},
    )
    with pytest.raises(DomainError) as exc:
        calculate_item(scheme, units=5)
    assert exc.value.code == "invalid_scheme"


def test_per_unit_unknown_tier_mode_raises():
    scheme = make_scheme(
        SalaryScheme.SchemeType.PER_UNIT_TIERED,
        {"base": 0, "tier_mode": "stepwise", "tiers": [{"upto": None, "rate": 100}]},
    )
    with pytest.raises(DomainError) as exc:
        calculate_item(scheme, units=1)
    assert exc.value.code == "invalid_scheme"


def test_unknown_scheme_type_raises():
    scheme = make_scheme("lottery", {"base": 100})
    with pytest.raises(DomainError) as exc:
        calculate_item(scheme)
    assert exc.value.code == "invalid_scheme"
