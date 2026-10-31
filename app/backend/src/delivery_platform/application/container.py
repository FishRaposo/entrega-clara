"""Composition root: builds adapters and exposes them to the API layer.

Configuration selects the active persistence mode. M1 ships the memory adapter;
the PostgreSQL adapter is a documented future expansion implementing the same
unit-of-work port.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from delivery_platform.adapters.memory.clock import DeterministicClock
from delivery_platform.adapters.memory.events import InProcessEventHub
from delivery_platform.adapters.memory.ids import SequentialIds
from delivery_platform.adapters.memory.payment import SimulatedPaymentGateway
from delivery_platform.adapters.memory.routing import StraightLineRoutePlanner
from delivery_platform.adapters.memory.store import MemoryStore
from delivery_platform.adapters.memory.unit_of_work import MemoryUnitOfWork
from delivery_platform.application.context import CommandContext
from delivery_platform.application.identity import IdentityContext
from delivery_platform.application.lifecycle import LifecycleRecorder
from delivery_platform.application.ports import DeliveryRoutePlanner
from delivery_platform.core.config import Settings
from delivery_platform.domain.entities import DemoIdentity
from delivery_platform.domain.errors import MissingIdentityError
from delivery_platform.routing.graph import load_graph
from delivery_platform.routing.graph_planner import GraphRoutePlanner

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[5]
_GRAPH_PATH = _REPO_ROOT / "data" / "graph" / "sao-paulo-centro.json"


@dataclass
class AppContainer:
    settings: Settings
    store: MemoryStore = field(default_factory=MemoryStore)
    publisher: InProcessEventHub = field(default_factory=InProcessEventHub)
    clock: DeterministicClock = field(default_factory=DeterministicClock)
    ids: SequentialIds = field(default_factory=SequentialIds)
    payment_gateway: SimulatedPaymentGateway = field(
        default_factory=SimulatedPaymentGateway
    )
    route_planner: DeliveryRoutePlanner = field(
        default_factory=StraightLineRoutePlanner
    )

    def uow(self) -> MemoryUnitOfWork:
        return MemoryUnitOfWork(self.store, self.publisher)

    def recorder(self, uow: MemoryUnitOfWork, ctx: CommandContext) -> LifecycleRecorder:
        return LifecycleRecorder(uow=uow, ctx=ctx, clock=self.clock, ids=self.ids)

    def resolve_identity(self, identity_id: str | None) -> IdentityContext:
        """Map a demo-identity header value to a server-known identity."""
        if not self.settings.demo_mode or not identity_id:
            raise MissingIdentityError()
        identity = self.store.identities.get(identity_id)
        if identity is None:
            raise MissingIdentityError()
        return IdentityContext.from_demo_identity(identity)


def build_container(settings: Settings) -> AppContainer:
    if settings.persistence_mode != "memory":
        raise RuntimeError(
            "PERSISTENCE_MODE=postgres is a documented future expansion; "
            "the PostgreSQL adapter is not implemented yet."
        )
    container = AppContainer(settings=settings)
    try:
        container.route_planner = GraphRoutePlanner(load_graph(_GRAPH_PATH))
    except (OSError, TypeError, ValueError) as error:
        logger.warning(
            "Synthetic graph unavailable at %s (%s); falling back to straight-line routing",
            _GRAPH_PATH,
            error,
        )
    return container


def seed_identities(container: AppContainer, identities: list[DemoIdentity]) -> None:
    """Reference-data hook used by the seed loader and tests."""
    for identity in identities:
        container.store.identities[identity.id] = identity
