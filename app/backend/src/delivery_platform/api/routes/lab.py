"""Algorithm lab API — bounded, deterministic routing experiments.

Read-only with respect to domain state: every request builds its own problem
and returns solver metadata, so the lab never touches orders/deliveries.
"""

import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Protocol

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from delivery_platform.api.deps import get_identity
from delivery_platform.application.container import (
    graph_path,
    load_graph_document,
    load_traffic_profile,
)
from delivery_platform.application.identity import IdentityContext
from delivery_platform.core.config import settings
from delivery_platform.routing.ch import ChPathSolver
from delivery_platform.routing.graph import StreetGraph
from delivery_platform.routing.informed import (
    AltPathSolver,
    BidirectionalPathSolver,
    WeightedAStarSolver,
)
from delivery_platform.routing.landmarks import DEFAULT_LANDMARK_COUNT
from delivery_platform.routing.matrix import build_cost_matrix
from delivery_platform.routing.path import (
    AStarPathSolver,
    DijkstraPathSolver,
    PathProblem,
    PathResult,
)
from delivery_platform.routing.time_dependent import (
    TimeDependentAStarPathSolver,
    TimeDependentDijkstraPathSolver,
)
from delivery_platform.routing.time_profile import TravelTimeProfile
from delivery_platform.routing.tsp import (
    HeldKarpSolver,
    NearestNeighborSolver,
    TwoOptSolver,
)

router = APIRouter(prefix="/lab", tags=["lab"])

IdentityDep = Annotated[IdentityContext, Depends(get_identity)]

BENCHMARK_PATH = Path(__file__).resolve().parents[6] / "docs" / "benchmarks" / "routing.json"

PathSolverName = Literal[
    "astar",
    "dijkstra",
    "alt",
    "bidirectional",
    "ch",
    "td-astar",
    "td-dijkstra",
    "weighted-astar",
]
TspSolverName = Literal["held-karp", "nearest-neighbor", "two-opt"]
Objective = Literal["time", "distance"]
GraphName = Literal["default", "osm", "synthetic"]

_TSP_SOLVERS: dict[
    str,
    type[HeldKarpSolver] | type[NearestNeighborSolver] | type[TwoOptSolver],
] = {
    "held-karp": HeldKarpSolver,
    "nearest-neighbor": NearestNeighborSolver,
    "two-opt": TwoOptSolver,
}

MAX_LAB_STOPS = 10


class TracePathSolver(Protocol):
    """What the lab needs from any rung of the ladder: a traceable solve."""

    def solve(self, problem: PathProblem, *, trace: bool = False) -> PathResult: ...


def build_path_solver(
    name: PathSolverName, *, epsilon: float, landmarks: int
) -> TracePathSolver:
    """Picker for the solver ladder: exact, accelerated, or inexact-but-faster."""
    if name == "astar":
        return AStarPathSolver()
    if name == "dijkstra":
        return DijkstraPathSolver()
    if name == "alt":
        return AltPathSolver(landmarks=landmarks)
    if name == "bidirectional":
        return BidirectionalPathSolver(landmarks=landmarks)
    if name == "ch":
        return ChPathSolver()
    if name == "td-astar":
        return TimeDependentAStarPathSolver()
    if name == "td-dijkstra":
        return TimeDependentDijkstraPathSolver()
    return WeightedAStarSolver(epsilon=epsilon)


@lru_cache(maxsize=4)
def _graph(name: GraphName = "default") -> StreetGraph:
    """Load a graph document once per process; the lab is read-only."""
    path = graph_path(settings, name)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail=f"graph '{name}' is not available")
    try:
        return load_graph_document(str(path))
    except (OSError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=503, detail=f"graph '{name}' could not be loaded"
        ) from error


class PathExperimentRequest(BaseModel):
    origin: str
    destination: str
    solver: PathSolverName = "astar"
    objective: Objective = "time"
    trace: bool = False
    graph: GraphName = "default"
    # Only used by the landmark-based solvers / the inexact weighted variant.
    epsilon: float = Field(default=2.0, ge=1.0, le=10.0)
    landmarks: int = Field(default=DEFAULT_LANDMARK_COUNT, ge=1, le=32)
    # Only used by the time-dependent solvers: local hour of the departure.
    departure_hour: float | None = Field(default=None, ge=0.0, lt=24.0)


class TspExperimentRequest(BaseModel):
    nodes: list[str] = Field(min_length=3, max_length=MAX_LAB_STOPS)
    solver: TspSolverName = "two-opt"
    objective: Objective = "time"
    origin_index: int = Field(default=0, ge=0)
    graph: GraphName = "default"


def _path_payload(result: PathResult, problem: PathProblem) -> dict:
    graph = problem.graph
    cost = result.estimated_seconds if problem.objective == "time" else result.distance_meters
    return {
        "node_path": list(result.node_path),
        "expanded_order": list(result.expanded_order or ()),
        "frontier_sizes": list(result.frontier_sizes or ()),
        "expansion_costs": list(result.expansion_costs or ()),
        "distance_meters": result.distance_meters,
        "estimated_seconds": result.estimated_seconds,
        "cost": cost,
        "solver_name": result.solver_name,
        "solver_version": result.solver_version,
        "nodes_expanded": result.nodes_expanded,
        "computation_time_ns": result.computation_time_ns,
        "preprocessing_time_ns": result.preprocessing_time_ns,
        "departure_at": result.departure_at,
        "arrival_at": result.arrival_at,
        "objective": problem.objective,
        "geometry": [
            [graph.nodes[n].longitude, graph.nodes[n].latitude]
            for n in result.node_path
        ],
    }


@router.get("/graph")
def lab_graph(_identity: IdentityDep, graph: GraphName = "default") -> dict:
    """Compact graph payload: index-aligned arrays keep a 15k-node graph small."""
    document = _graph(graph)
    ids = list(document.nodes)
    index_of = {node: position for position, node in enumerate(ids)}
    return {
        "graph_id": document.graph_id,
        "version": document.version,
        "source": document.source,
        "attribution": document.attribution,
        "max_speed_mps": document.max_speed_mps,
        "node_count": len(ids),
        "edge_count": sum(len(edges) for edges in document.adjacency.values()),
        "ids": ids,
        "nodes": [
            [round(document.nodes[node].latitude, 6), round(document.nodes[node].longitude, 6)]
            for node in ids
        ],
        "edges": [
            [index_of[node], index_of[edge.to_node], edge.speed_kmh]
            for node, edges in document.adjacency.items()
            for edge in edges
        ],
    }


@router.post("/path")
def lab_path(
    payload: PathExperimentRequest,
    _identity: IdentityDep,
) -> dict:
    graph = _graph(payload.graph)
    if payload.origin not in graph.nodes or payload.destination not in graph.nodes:
        raise HTTPException(status_code=400, detail="unknown node id")
    solver = build_path_solver(
        payload.solver, epsilon=payload.epsilon, landmarks=payload.landmarks
    )
    time_dependent = payload.solver in ("td-astar", "td-dijkstra")
    profile = load_traffic_profile(settings) if time_dependent else None
    departure: float | None = None
    if time_dependent:
        if profile is None:
            raise HTTPException(status_code=409, detail="traffic profile unavailable")
        if payload.departure_hour is None:
            raise HTTPException(
                status_code=400, detail="time-dependent solvers require departure_hour"
            )
        departure = _local_hour_epoch(profile, payload.departure_hour)
    problem = PathProblem(
        graph,
        payload.origin,
        payload.destination,
        payload.objective,
        departure,
        profile,
    )
    result = solver.solve(problem, trace=payload.trace)
    return _path_payload(result, problem)


def _local_hour_epoch(profile: TravelTimeProfile, hour: float) -> float:
    """Epoch at a given local hour of a fixed reference day (deterministic)."""
    midnight = datetime(2026, 1, 1, tzinfo=UTC).timestamp() - profile.tz_offset_hours * 3600.0
    return midnight + hour * 3600.0


@router.get("/traffic")
def lab_traffic(
    _identity: IdentityDep,
    origin: str,
    destination: str,
    graph: GraphName = "default",
) -> dict:
    """ETA of the same trip for every hour of the day under the traffic profile."""
    document = _graph(graph)
    if origin not in document.nodes or destination not in document.nodes:
        raise HTTPException(status_code=400, detail="unknown node id")
    profile = load_traffic_profile(settings)
    if profile is None:
        raise HTTPException(status_code=409, detail="traffic profile unavailable")
    static = DijkstraPathSolver().solve(PathProblem(document, origin, destination, "time"))
    solver = TimeDependentAStarPathSolver()
    points: list[dict] = []
    for hour in range(24):
        result = solver.solve(
            PathProblem(
                document,
                origin,
                destination,
                "time",
                _local_hour_epoch(profile, float(hour)),
                profile,
            )
        )
        points.append(
            {
                "hour": hour,
                "estimated_seconds": round(result.estimated_seconds, 3),
                "distance_meters": round(result.distance_meters, 1),
            }
        )
    peak = max(points, key=lambda point: point["estimated_seconds"])
    night = min(points, key=lambda point: point["estimated_seconds"])
    return {
        "profile_id": profile.profile_id,
        "profile_source": profile.source,
        "static_seconds": round(static.estimated_seconds, 3),
        "points": points,
        "peak_hour": peak["hour"],
        "peak_seconds": peak["estimated_seconds"],
        "night_hour": night["hour"],
        "night_seconds": night["estimated_seconds"],
    }


@router.post("/tsp")
def lab_tsp(
    payload: TspExperimentRequest,
    _identity: IdentityDep,
) -> dict:
    graph = _graph(payload.graph)
    unknown = [n for n in payload.nodes if n not in graph.nodes]
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown nodes: {unknown}")
    if payload.origin_index >= len(payload.nodes):
        raise HTTPException(status_code=400, detail="origin_index out of range")
    problem = build_cost_matrix(
        graph,
        labels=tuple(payload.nodes),
        nodes=tuple(payload.nodes),
        objective=payload.objective,
        origin_index=payload.origin_index,
    )
    solver = _TSP_SOLVERS[payload.solver]()
    result = solver.solve(problem)
    return {
        "route": list(result.route),
        "total_cost": result.total_cost,
        "solver_name": result.solver_name,
        "execution_time_ns": result.execution_time_ns,
        "routes_evaluated": result.routes_evaluated,
        "objective": payload.objective,
    }


@router.get("/benchmarks")
def lab_benchmarks(_identity: IdentityDep) -> dict:
    if not BENCHMARK_PATH.exists():
        raise HTTPException(status_code=404, detail="benchmark artifacts not generated")
    return json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
