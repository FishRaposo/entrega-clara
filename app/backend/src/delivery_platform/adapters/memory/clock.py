"""Deterministic clock: time advances only through explicit commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass
class DeterministicClock:
    """A seeded clock for demo, tests, and replay — never wall-clock."""

    current: datetime = field(
        default_factory=lambda: datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)
    )

    def now(self) -> datetime:
        return self.current

    def advance_minutes(self, minutes: float) -> datetime:
        if minutes < 0:
            raise ValueError("clock cannot move backwards")
        self.current = self.current + timedelta(minutes=minutes)
        return self.current
