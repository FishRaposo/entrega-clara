"""API dependencies: container access, identity resolution, command context."""

from __future__ import annotations

import uuid

from fastapi import Header, Request

from delivery_platform.application.container import AppContainer
from delivery_platform.application.context import CommandContext
from delivery_platform.application.identity import IdentityContext
from delivery_platform.domain.errors import DomainError


def get_container(request: Request) -> AppContainer:
    return request.app.state.container  # type: ignore[no-any-return]


def get_identity(
    request: Request,
    x_demo_identity: str | None = Header(default=None),
) -> IdentityContext:
    return get_container(request).resolve_identity(x_demo_identity)


def command_context(
    request: Request,
    x_demo_identity: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> CommandContext:
    correlation_id = getattr(request.state, "correlation_id", None) or f"cor_{uuid.uuid4().hex[:12]}"
    return CommandContext(
        identity=get_container(request).resolve_identity(x_demo_identity),
        correlation_id=correlation_id,
        command_id=f"cmd_{uuid.uuid4().hex[:12]}",
        idempotency_key=idempotency_key,
    )


def require_idempotency_key(ctx: CommandContext) -> None:
    if not ctx.idempotency_key:
        raise DomainError("A chave de idempotência é obrigatória.")
