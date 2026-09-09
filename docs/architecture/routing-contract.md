# Routing contract

Routing consumers depend on `RouteProblem`, `RouteResult`, and the `RouteSolver`
protocol instead of a concrete algorithm. `RouteProblem` is a validated, immutable
complete cost matrix with at least two labels and a valid origin index. Costs must be
finite, numeric, and non-negative.

`RouteResult` reports a closed ordered `route`, its `total_cost`, the `solver_name`,
`execution_time_ns`, and `routes_evaluated`. A solver may include `route_history`
only for bounded experiments; consumers must treat it as optional.

`LegacyBruteForceTSPSolver` is deliberately retained as the original exact,
zero-origin permutation baseline for small matrices. It is a portfolio comparison
reference, not the production dispatch strategy. Its timing covers solver computation
only and excludes rendering, networking, and other application work.

## M1 delivery-route extension

The matrix contract above remains the legacy/algorithm-laboratory contract. M1 adds a
separate shortest-path contract rather than pretending that a cost matrix is a road
graph:

| Contract | Required fields | Result |
| --- | --- | --- |
| `PathProblem` | graph ID/version, origin node, destination node, cost assumptions | validated graph traversal input |
| `PathResult` | ordered nodes, geometry, distance, estimated seconds, solver/version, nodes expanded | one route segment |
| `DeliveryRouteProblem` | courier origin, restaurant pickup, customer drop-off, graph/version, deterministic seed | two-leg delivery input |
| `DeliveryRouteResult` | ordered stops, route segments, GeoJSON geometry, distance/ETA, solver/version, metrics, warnings | provider-neutral route consumed by courier/map surfaces |

The live M1 solver is local A* over a versioned synthetic graph. Dijkstra is a bounded
test oracle. The result must visit the restaurant before the customer, include every
required stop exactly once, and carry the graph version that produced it. The
frontend may render the result with MapLibre/MapTiler, but routing code must not import
map-provider SDKs.

Future multi-stop optimization extends `DeliveryRouteProblem` with precedence,
capacity, time windows, and objective constraints. Dispatch assignment is a separate
problem and must not be smuggled into the shortest-path contract.
