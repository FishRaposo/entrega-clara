import pytest
from delivery_platform.domain.money import CartTotals, Money, compute_totals


def test_money_add_subtract_multiply():
    price = Money(2590)

    assert price.times(2) == Money(5180)
    assert price.add(Money(500)) == Money(3090)
    assert price.subtract(Money(590)) == Money(2000)


def test_money_rejects_non_integer_and_negative_amounts():
    with pytest.raises(TypeError):
        Money(10.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Money(True)
    with pytest.raises(ValueError):
        Money(-1)


def test_money_requires_matching_currencies():
    with pytest.raises(ValueError):
        Money(100, "BRL").add(Money(100, "CAD"))


def test_compute_totals_applies_discount_before_fee():
    totals = compute_totals([(2590, 2)], discount_minor=500, delivery_fee_minor=800)

    assert totals.subtotal_minor == 5180
    assert totals.discount_minor == 500
    assert totals.delivery_fee_minor == 800
    assert totals.total_minor == 5480
    assert totals.currency == "BRL"


def test_compute_totals_clamps_discount_at_subtotal():
    totals = compute_totals([(1000, 1)], discount_minor=5000, delivery_fee_minor=300)

    assert totals.discount_minor == 1000
    assert totals.total_minor == 300


def test_cart_totals_rejects_inconsistent_sum():
    with pytest.raises(ValueError):
        CartTotals(subtotal_minor=1000, discount_minor=100, delivery_fee_minor=0, total_minor=1)
