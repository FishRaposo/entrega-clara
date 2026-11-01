# ADR 0011 — Capacity, promised windows and dynamic re-planning

Status: accepted. Implemented by `routing/vrp.py`, `routing/graph_planner.py`,
`application/commands/courier.py`, `POST /courier/batches/{id}/insert` and the
`route.replanned` event.

## Context

The batch optimizer knew about precedence and travel time, and nothing else. It
could not answer the questions dispatch actually asks: *does this order fit in
the courier's bag?*, *will the customer get it inside the promised window?*, and
*the courier is already en route — can another order join without breaking the
existing promises?*

Those are not cosmetic constraints. A tour that ignores capacity is infeasible
in practice; a tour that ignores windows is late; and a re-plan that sends a
courier back to a restaurant they already left is worse than not re-planning at
all.

## Decision

1. **Model the problem as a capacitated VRP with windows and precedence**
   (`routing/vrp.py`): stops carry a signed volume delta, a service time and an
   optional window; the matrix supplies travel seconds; a pickup must precede
   its drop-off. Times are **relative seconds from departure**, so the model is
   clock-free and every number is comparable in tests.
2. **Windows are soft inside the optimizer and hard at dispatch.** The solver
   prices lateness (`lateness_penalty`), so it can explain *how* late a plan is;
   the dispatcher decides whether that is acceptable through
   `max_lateness_seconds` (default 0 = hard). Rejections surface as
   `batch_infeasible` (409) with a message that distinguishes capacity from a
   missed window.
3. **Two solvers, one contract.** `ExactWindowSolver` enumerates orders with
   precedence and capacity pruning up to 8 stops (the demo's 2–3 deliveries are
   ≤ 6 stops); `InsertionWindowSolver` does cheapest feasible insertion plus
   relocate/swap local search above that. Tests assert the heuristic is never
   better than exact and that both respect precedence and capacity.
4. **The product promises what the customer is told.** `batch_accept` derives a
   window from the order's creation (20 minutes kitchen prep, 45-minute promise)
   and a volume from the order size, then hands both to the planner. Each
   route stop carries `planned_arrival_at` and `promised_until`; the route
   carries `wait_seconds`, `lateness_seconds` and `capacity_used`.
5. **Dynamic insertion re-plans only what is still ahead.** `POST
   /courier/batches/{id}/insert` adds an offered delivery to an active batch and
   re-optimizes the **remaining** stops from the courier's current position. An
   order already picked up contributes a drop-off only, and its volume starts
   on board (`initial_load`), so the optimizer never routes the courier back to
   a restaurant. The previous plan is replaced, deliveries and order states are
   updated in the same transaction, and a `route.replanned` event records the
   stop count and the ETA delta.
6. **The baseline comparison stays honest.** The console previously compared the
   exact tour against nearest-neighbour over the same matrix. With constraints,
   the honest baseline is the order the deliveries were offered in, priced on
   the same matrix (`offered-order`), so the number shows what optimizing the
   stop order bought without pretending the heuristic obeyed the constraints.

## Measured/verified behaviour

* Exact search over ≤ 6 stops runs in well under a millisecond on the centro
  graph (the solver enumerates precedence-valid orders and prunes).
* A batch whose window has already expired is rejected with `batch_infeasible`
  and a window message; a volume larger than the courier's capacity is rejected
  with a capacity message; a batch that fits is planned with per-stop arrivals
  inside the promises.
* A re-plan after one pickup produces exactly five stops for three deliveries
  (drop-off of the picked-up order, pickup + drop-off of the other assigned
  order, pickup + drop-off of the new order) — asserted over the HTTP API, not
  just the planner.
* The `route.replanned` event carries the new stop count and the ETA delta.

## Consequences

* The demo flow (`batch_accept` → pickups → deliveries) keeps working unchanged;
  the new constraints are visible in the courier console (per-stop times,
  capacity, waiting) and in the typed rejection path.
* Batch size is capped at 4 deliveries for insertion, while acceptance keeps the
  2–3 rule; the extra slot exists because an en-route insertion is the case the
  cap was not designed around. The limit lives in `MAX_BATCH_DELIVERIES`.
* Matrix cells for a time-dependent batch are still priced from the batch
  departure (no accumulation), while the legs and the VRP schedule accumulate
  exactly. This is the documented approximation from ADR 0010, unchanged.
* A future dispatcher upgrade (real time windows from merchants, multi-courier
  assignment) can reuse the same VRP contract; only the request builder moves.

## Rejected alternatives

* **Hard windows inside the solver.** Then an instance with one impossible
  promise has no solution at all, and dispatch cannot tell "late by 30 seconds"
  from "physically impossible". Soft pricing plus a dispatch threshold answers
  both.
* **Insertion as a new tour from scratch.** Correct but wasteful and it loses
  the property that already-completed stops are never re-visited; the
  remaining-stops model encodes that property structurally.
* **Capacity on the order's item count only.** Volume is a routing input, not a
  marketing attribute; keeping it in the batch request lets the demo and tests
  set it explicitly.
