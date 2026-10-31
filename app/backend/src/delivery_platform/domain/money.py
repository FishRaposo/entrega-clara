"""Money semantics: integer minor units plus an explicit currency."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    """An amount in integer minor units (centavos for BRL)."""

    amount_minor: int
    currency: str = "BRL"

    def __post_init__(self) -> None:
        if isinstance(self.amount_minor, bool) or not isinstance(self.amount_minor, int):
            raise TypeError("Money amount must be an integer minor-unit value")
        if self.amount_minor < 0:
            raise ValueError("Money amount must not be negative")
        if not self.currency:
            raise ValueError("Money requires an explicit currency")

    def add(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount_minor + other.amount_minor, self.currency)

    def subtract(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount_minor - other.amount_minor, self.currency)

    def times(self, factor: int) -> Money:
        if isinstance(factor, bool) or not isinstance(factor, int) or factor < 0:
            raise ValueError("Money multiplier must be a non-negative integer")
        return Money(self.amount_minor * factor, self.currency)

    def _require_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError("Money operations require the same currency")


@dataclass(frozen=True)
class CartTotals:
    """Authoritative cart/order totals in minor units."""

    subtotal_minor: int
    discount_minor: int
    delivery_fee_minor: int
    total_minor: int
    currency: str = "BRL"

    def __post_init__(self) -> None:
        for name in ("subtotal_minor", "discount_minor", "delivery_fee_minor", "total_minor"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.total_minor != self.subtotal_minor - self.discount_minor + self.delivery_fee_minor:
            raise ValueError("Totals must satisfy subtotal - discount + fee = total")
        if not self.currency:
            raise ValueError("Totals require an explicit currency")


def compute_totals(
    line_amounts: list[tuple[int, int]],
    *,
    discount_minor: int = 0,
    delivery_fee_minor: int = 0,
    currency: str = "BRL",
) -> CartTotals:
    """Compute totals from (unit_price_minor, quantity) lines.

    A discount larger than the subtotal clamps at the subtotal; it can never
    produce a negative or fee-skipping total.
    """
    subtotal = sum(price * quantity for price, quantity in line_amounts)
    discount = min(discount_minor, subtotal)
    return CartTotals(
        subtotal_minor=subtotal,
        discount_minor=discount,
        delivery_fee_minor=delivery_fee_minor,
        total_minor=subtotal - discount + delivery_fee_minor,
        currency=currency,
    )
