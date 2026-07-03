"""Деньги: единая точка квантования.

SQLite теряет масштаб у Sum()-агрегатов (Decimal("1000") вместо "1000.00") —
все денежные агрегаты перед сериализацией проходят через q2().
"""
from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")


def q2(value) -> Decimal:
    """Любое денежное значение → Decimal с ровно 2 знаками (ROUND_HALF_UP)."""
    if value is None:
        value = 0
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
