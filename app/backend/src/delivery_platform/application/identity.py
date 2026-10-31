"""Identity context resolved before any application service runs."""

from __future__ import annotations

from dataclasses import dataclass, field

from delivery_platform.domain.entities import DemoIdentity, Role


@dataclass(frozen=True)
class IdentityContext:
    """The server-resolved actor. A client can never grant itself a role."""

    identity_id: str
    role: Role
    market: str = "br"
    scopes: frozenset[str] = field(default_factory=frozenset)
    source: str = "demo"
    restaurant_id: str | None = None
    courier_id: str | None = None

    @classmethod
    def from_demo_identity(cls, identity: DemoIdentity) -> IdentityContext:
        return cls(
            identity_id=identity.id,
            role=identity.role,
            market=identity.market,
            restaurant_id=identity.restaurant_id,
            courier_id=identity.courier_id,
        )
