"""Composition root: builds adapters and exposes them to the API layer.

Configuration selects the active persistence mode. M1 ships the memory adapter;
the PostgreSQL adapter is a documented future expansion implementing the same
unit-of-work port.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

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
from delivery_platform.application.ports import DeliveryRoutePlanner, UnitOfWork
from delivery_platform.core.config import Settings
from delivery_platform.domain.entities import DemoIdentity
from delivery_platform.domain.errors import MissingIdentityError
from delivery_platform.routing.graph import StreetGraph, load_graph
from delivery_platform.routing.graph_planner import GraphRoutePlanner
from delivery_platform.routing.time_profile import TravelTimeProfile, load_profile

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[5]
_GRAPH_DIR = _REPO_ROOT / "data" / "graph"

# Named graph documents: the centro extract powers the product and the lab, the
# synthetic lattice is the deterministic fixture and offline fallback, and the
# city-scale graph is the benchmark/dispatch artifact (compressed compact-v1).
GRAPH_FILES: dict[str, str] = {
    "osm": "sao-paulo-centro-osm.json",
    "synthetic": "sao-paulo-centro.json",
    "city": "sao-paulo-city.json.gz",
}
# Preference order when no explicit path is configured: the real street extract
# first, the deterministic synthetic lattice as the offline fallback.
DEFAULT_GRAPH_ORDER = ("osm", "synthetic")


def graph_path(settings: Settings, name: str = "default") -> Path | None:
    """Resolve a graph document by name, honoring the configured override."""
    if name == "default":
        if settings.routing_graph_path:
            explicit = Path(settings.routing_graph_path)
            return explicit if explicit.is_absolute() else _REPO_ROOT / explicit
        for candidate_name in DEFAULT_GRAPH_ORDER:
            candidate = _GRAPH_DIR / GRAPH_FILES[candidate_name]
            if candidate.exists():
                return candidate
        return _GRAPH_DIR / GRAPH_FILES[DEFAULT_GRAPH_ORDER[0]]
    file_name = GRAPH_FILES.get(name)
    return _GRAPH_DIR / file_name if file_name else None


@lru_cache(maxsize=4)
def load_graph_document(path: str) -> StreetGraph:
    """Parse a graph document once per process; loaded graphs are immutable."""
    return load_graph(path)


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
    #: Set only in persistent mode: builds a UoW over the loaded snapshot.
    uow_factory: Callable[[], UnitOfWork] | None = None
    persistence: Any | None = None
    persistence_version: int = 0

    def uow(self) -> UnitOfWork:
        if self.uow_factory is not None:
            return self.uow_factory()
        return MemoryUnitOfWork(self.store, self.publisher)

    def recorder(self, uow: UnitOfWork, ctx: CommandContext) -> LifecycleRecorder:
        return LifecycleRecorder(uow=uow, ctx=ctx, clock=self.clock, ids=self.ids)

    def resolve_identity(self, identity_id: str | None) -> IdentityContext:
        """Map a demo-identity header value to a server-known identity."""
        if not self.settings.demo_mode or not identity_id:
            raise MissingIdentityError()
        identity = self.store.identities.get(identity_id)
        if identity is None:
            raise MissingIdentityError()
        return IdentityContext.from_demo_identity(identity)


def load_traffic_profile(settings: Settings) -> TravelTimeProfile | None:
    """Load the traffic profile once; a missing or broken profile means static routing."""
    configured = settings.traffic_profile_path
    path = Path(configured) if configured else _GRAPH_DIR / "traffic-profile.json"
    if configured and not path.is_absolute():
        path = _REPO_ROOT / path
    if not path.exists():
        logger.warning("Traffic profile %s is not available; routing stays static", path)
        return None
    try:
        return load_profile(path)
    except (OSError, ValueError):
        logger.exception("Traffic profile %s is unusable; routing stays static", path)
        return None


def _load_route_planner(settings: Settings) -> DeliveryRoutePlanner | None:
    """Load the configured graph; fall back graph by graph, then to straight lines."""
    profile = load_traffic_profile(settings)
    candidates: list[Path] = []
    if settings.routing_graph_path:
        explicit = graph_path(settings)
        if explicit is not None:
            candidates.append(explicit)
    candidates.extend(_GRAPH_DIR / GRAPH_FILES[name] for name in DEFAULT_GRAPH_ORDER)
    for candidate in candidates:
        if not candidate.exists():
            logger.warning("Routing graph %s is not available", candidate)
            continue
        try:
            return GraphRoutePlanner(load_graph_document(str(candidate)), profile)
        except (OSError, TypeError, ValueError) as error:
            logger.warning("Routing graph %s could not be loaded (%s)", candidate, error)
    logger.warning("No usable routing graph; falling back to straight-line routing")
    return None


def build_container(settings: Settings) -> AppContainer:
    container = AppContainer(settings=settings)
    planner = _load_route_planner(settings)
    if planner is not None:
        container.route_planner = planner
    if settings.persistence_mode == "memory":
        return container
    if settings.persistence_mode != "postgres":
        raise RuntimeError(f"Unknown PERSISTENCE_MODE {settings.persistence_mode!r}")
    try:
        from delivery_platform.adapters.postgres.store import (
            PostgresStore,
            PostgresUnavailable,
            adopt_store,
        )
        from delivery_platform.adapters.postgres.unit_of_work import PostgresUnitOfWork
    except ImportError as error:
        raise RuntimeError(
            "PERSISTENCE_MODE=postgres requires the optional extra: "
            "pip install -e 'app/backend[postgres]'"
        ) from error
    try:
        store = PostgresStore.from_url(settings.database_url)
        store.migrate()
        snapshot, version = store.load()
    except PostgresUnavailable:
        raise
    except Exception as error:
        raise RuntimeError(
            f"PERSISTENCE_MODE=postgres could not reach the database: {error}"
        ) from error
    # Boot with the persisted snapshot; every unit of work reloads it inside a
    # transaction, so this copy is only the process's reference for reads.
    adopt_store(container.store, snapshot)
    container.persistence = store
    container.persistence_version = version
    container.uow_factory = lambda: PostgresUnitOfWork(store, container.store, container.publisher)
    return container


def seed_identities(container: AppContainer, identities: list[DemoIdentity]) -> None:
    """Reference-data hook used by the seed loader and tests."""
    for identity in identities:
        container.store.identities[identity.id] = identity
