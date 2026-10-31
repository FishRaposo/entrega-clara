"""Algorithm lab API — bounded, deterministic routing experiments.

Read-only with respect to domain state: every request builds its own problem
and returns solver metadata, so the lab never touches orders/deliveries.
"""

import json
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from delivery_platform.api.deps import get_identity
from delivery_platform.application.identity import IdentityContext
from delivery_platform.routing.graph import load_graph
from delivery_platform.routing.matrix import build_cost_matrix
from delivery_platform.routing.path import (
    AStarPathSolver,
    DijkstraPathSolver,
    PathProblem,
)
from delivery_platform.routing.tsp import (
    HeldKarpSolver,
    NearestNeighborSolver,
    TwoOptSolver,
)

router = APIRouter(prefix="/lab", tags=["lab"])

IdentityDep = Annotated[IdentityContext, Depends(get_identity)]

GRAPH_PATH = Path("data/graph/sao-paulo-centro.json")
BENCHMARK_PATH = Path("docs/benchmarks/routing.json")

PathSolverName = Literal["astar", "dijkstra"]
TspSolverName = Literal["held-karp", "nearest-neighbor", "two-opt"]
Objective = Literal["time", "distance"]

_PATH_SOLVERS: dict[str, type[AStarPathSolver] | type[DijkstraPathSolver]] = {
    "astar": AStarPathSolver,
    "dijkstra": DijkstraPathSolver,
}
_TSP_SOLVERS: dict[
    str,
    type[HeldKarpSolver] | type[NearestNeighborSolver] | type[TwoOptSolver],
] = {
    "held-karp": HeldKarpSolver,
    "nearest-neighbor": NearestNeighborSolver,
    "two-opt": TwoOptSolver,
}

MAX_LAB_STOPS = 10


def _graph():
    return load_graph(GRAPH_PATH)


class PathExperimentRequest(BaseModel):
    origin: str
    destination: str
    solver: PathSolverName = "astar"
    objective: Objective = "time"
    trace: bool = False


class TspExperimentRequest(BaseModel):
    nodes: list[str] = Field(min_length=3, max_length=MAX_LAB_STOPS)
    solver: TspSolverName = "two-opt"
    objective: Objective = "time"
    origin_index: int = Field(default=0, ge=0)


def _path_payload(result, problem: PathProblem) -> dict:
    graph = problem.graph
    return {
        "node_path": list(result.node_path),
        "expanded_order": list(result.expanded_order or ()),
        "distance_meters": result.distance_meters,
        "estimated_seconds": result.estimated_seconds,
        "solver_name": result.solver_name,
        "solver_version": result.solver_version,
        "nodes_expanded": result.nodes_expanded,
        "computation_time_ns": result.computation_time_ns,
        "objective": problem.objective,
        "geometry": [
            [graph.nodes[n].longitude, graph.nodes[n].latitude]
            for n in result.node_path
        ],
    }


@router.get("/graph")
def lab_graph(_identity: IdentityDep) -> dict:
    graph = _graph()
    return {
        "graph_id": graph.graph_id,
        "version": graph.version,
        "max_speed_mps": graph.max_speed_mps,
        "nodes": [
            {"id": nid, "latitude": pt.latitude, "longitude": pt.longitude}
            for nid, pt in graph.nodes.items()
        ],
        "edges": [
            {"from": nid, "to": e.to_node, "speed_kmh": e.speed_kmh}
            for nid, edges in graph.adjacency.items()
            for e in edges
        ],
    }


@router.post("/path")
def lab_path(
    payload: PathExperimentRequest,
    _identity: IdentityDep,
) -> dict:
    graph = _graph()
    if payload.origin not in graph.nodes or payload.destination not in graph.nodes:
        raise HTTPException(status_code=400, detail="unknown node id")
    solver = _PATH_SOLVERS[payload.solver]()
    problem = PathProblem(
        graph, payload.origin, payload.destination, payload.objective
    )
    result = solver.solve(problem, trace=payload.trace)
    return _path_payload(result, problem)


@router.post("/tsp")
def lab_tsp(
    payload: TspExperimentRequest,
    _identity: IdentityDep,
) -> dict:
    graph = _graph()
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
