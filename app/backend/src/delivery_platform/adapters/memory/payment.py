"""Deterministic simulated payment gateway.

No card data, provider payloads, or credentials ever enter this adapter. The
demo caller may request an outcome via ``simulate_outcome``; without it the
configured default outcome applies.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from delivery_platform.domain.entities import PaymentAttempt, PaymentMethod

Outcome = Literal["approved", "declined"]


class SimulatedPaymentGateway:
    def __init__(self, default_outcome: Outcome = "approved") -> None:
        self._default_outcome = default_outcome

    def create_attempt(
        self,
        *,
        attempt_id: str,
        order_id: str,
        method: PaymentMethod,
        amount_minor: int,
        currency: str,
        simulate_outcome: str | None,
        idempotency_key_hash: str | None,
        now: datetime,
    ) -> PaymentAttempt:
        outcome = self._resolve_outcome(simulate_outcome)
        return PaymentAttempt(
            id=attempt_id,
            order_id=order_id,
            method=method,
            status=outcome,
            safe_reference=f"pay_ref_{attempt_id}",
            failure_code=None if outcome == "approved" else "declined_generic",
            idempotency_key_hash=idempotency_key_hash,
            created_at=now,
            updated_at=now,
        )

    def _resolve_outcome(self, simulate_outcome: str | None) -> Outcome:
        if simulate_outcome == "declined":
            return "declined"
        if simulate_outcome == "approved":
            return "approved"
        return self._default_outcome
