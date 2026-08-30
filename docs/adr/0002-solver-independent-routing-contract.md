# ADR 0002: Solver-independent routing contract

## Status

Accepted

## Context

The project needs to preserve its brute-force travelling-salesperson implementation
as a correctness and portfolio baseline while allowing future routing algorithms to
replace it. Courier and operations layers must not become coupled to that legacy
implementation.

## Decision

Routing inputs and outputs are represented by immutable `RouteProblem` and
`RouteResult` models. Solver implementations satisfy the `RouteSolver` protocol.
The legacy brute-force solver is retained under an explicit legacy name, enumerates
all routes from origin index zero, and returns the common result contract.

## Consequences

Future solvers can be compared using identical problems and substituted without
rewriting route consumers. The legacy solver remains intentionally exponential and
is not a production dispatch strategy. Its optional route history is for small,
bounded experiments only.
