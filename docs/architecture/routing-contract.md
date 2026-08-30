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
