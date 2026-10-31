"""Command context carried by every state-changing request."""

from __future__ import annotations

from dataclasses import dataclass

from delivery_platform.application.identity import IdentityContext


@dataclass(frozen=True)
class CommandContext:
    identity: IdentityContext
    correlation_id: str
    command_id: str
    idempotency_key: str | None = None
    scenario_id: str | None = None
