"""Deterministic ID generator for reproducible fixtures and tests."""

from __future__ import annotations


class SequentialIds:
    """Prefix-scoped sequential IDs: ``order_000001``, ``evt_000002``, ..."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def new_id(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}_{self._counters[prefix]:06d}"
