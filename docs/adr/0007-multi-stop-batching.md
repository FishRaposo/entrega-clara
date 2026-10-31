# ADR 0007 — Multi-stop batching (one courier, several orders)

Status: accepted. The solver layer (cost-matrix builder, precedence-aware
Held-Karp/2-opt) is implemented and benchmarked; courier batch dispatch
integration is the remaining work.

## Context

M1 enforces one active delivery per courier. Real dispatch batches ready
orders going the same way — the exact problem our TSP solvers (Held-Karp,
2-opt with precedence) were built for.

## Decision

- Batching composes **two contracts**, not one: `build_cost_matrix` prices
  every stop pair via point-to-point A*; a `RouteSolver` then orders the
  stops under pickup-before-dropoff precedence. Dispatch stays out of the
  shortest-path contract (routing-contract.md).
- Solver of record for batch ordering: `HeldKarpSolver` — exact, bounded at
  18 stops, trivially satisfies 2–3 order batches (~≤7 stops).
- Precedence is expressed as `{dropoff_index: pickup_index}` maps passed to
  the solver, so a courier can never be routed to a customer before the
  restaurant that produced the order.
- Eligibility: orders in `ready_for_pickup` at the same restaurant may be
  batched into one delivery leg set; capacity is enforced at the dispatch
  boundary (batch size ≤ 3), not inside the TSP — a vehicle-capacity
  constraint is a dispatch concern.

## Consequences

- The courier console shows the computed stop sequence; the one-active-
  delivery invariant relaxes to one active *batch*.
- Cost: one matrix build per batch (O(stops²) A* runs) — bounded, cached
  per batch creation.
- Deferred: dynamic re-optimization mid-route, cross-restaurant batching,
  capacity by volume/weight.
