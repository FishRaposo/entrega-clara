# ADR 0010 — Time-dependent routing under a FIFO speed profile

Status: accepted. Implemented by `data/graph/traffic-profile.json`,
`routing/time_profile.py`, `routing/time_dependent.py`, the planner wiring in
`routing/graph_planner.py`, and `GET /lab/traffic`.

## Context

Every route the demo produced was priced on free-flow speed: a delivery at
11:55 and the same delivery at 23:00 got the same ETA. That is the largest
remaining gap between the routing core and the product claim it supports — a
delivery company's ETA is interesting *because* it depends on the hour.

Time-dependent shortest paths are subtle in a way static ones are not: if travel
time can decrease with departure time, a later departure can arrive earlier, and
then labelling the graph with a single earliest arrival per node is wrong —
waiting at a node could help. The standard requirement is **FIFO**: the arrival
function must be non-decreasing in departure time.

## Decision

1. **The profile is data, not code.** `data/graph/traffic-profile.json` holds
   three speed bands × 24 hourly multipliers, with the source labelled as
   *synthetic* in the file itself. A reader can inspect the exact assumption
   instead of reverse-engineering it from a demo.
2. **Multipliers are linearly interpolated between hourly buckets.** With
   arrival ``t + T·m(t)``, FIFO holds whenever ``T·|m'(t)| ≤ 1``. The loader
   rejects a profile that violates that bound for the slowest edge it may price
   (900 s by default, and the test suite also validates against the committed
   graph's slowest edge). A piecewise-constant profile would fail this check at
   every hour boundary where the peak ends — linear interpolation is not a
   cosmetic choice, it is what makes the model correct.
3. **Bands by free-flow speed, not by highway class.** The committed graph
   stores an edge's speed and distance, not its OSM class, so the profile groups
   roads at 25 km/h and 50 km/h. Class-accurate profiles would need ``highway``
   in the graph schema; that change is not worth a rebuild of both artifacts for
   a synthetic profile, and the limitation is stated where it matters.
4. **Time-dependent Dijkstra is the oracle; time-dependent A\* is the fast
   path.** Both search over arrival time. The A\* bound is
   ``distance · min_multiplier / max_speed`` — the network is never faster than
   its fastest multiplier, so the bound is admissible and consistent. Tests pin
   both against a Bellman-Ford reference on random graphs, and pin the whole
   machinery against static Dijkstra by feeding a flat (all 1.0) profile: the
   time-dependent solver must return the same path and the same cost.
5. **The product prices travel when it plans it.** Commands pass the clock's
   ``now``; the planner switches to ``td-astar`` and records ``departure_at``,
   ``arrival_at`` and ``traffic_profile_id`` on the route plan. Batch cells are
   priced from the batch departure (no accumulation inside the matrix) while the
   final legs accumulate exactly — a documented first-order approximation, not
   a hidden one.
6. **The lab shows the day.** ``GET /lab/traffic`` returns the same trip's ETA
   for all 24 local hours plus the free-flow cost, and the lab renders it as a
   bar strip with the peak and the quietest hour highlighted.

## Measured behaviour (committed centro graph)

* Lunch peak versus 23:30 on sampled pairs: every pair is slower at noon, and
  the average end-to-end ratio is **1.15×** — lower than the 1.5× of a single
  arterial edge, because the time-dependent search reroutes around the roads
  that slow down most. That damping is the phenomenon, not a bug.
* Rerouting is real: on sampled pairs the profile-optimal path is never worse
  than walking the free-flow path at noon, and is strictly better on part of
  them.
* Arrival is strictly increasing in departure time at every hour of the day on
  the whole 2,405-node graph.

## Consequences

* ``ROUTE_PLAN`` payloads gain ``departure_at``, ``arrival_at`` and
  ``traffic_profile_id``; the API and the courier console can show promise versus
  reality with the same clock that produced the promise.
* ETA accuracy (operations timeline) now compares a traffic-aware estimate with
  the delivered time, which is the comparison a dispatcher actually cares about.
* The city-scale benchmark stays on free-flow costs; time-dependent pricing at
  city scale would multiply the batch matrix cost by the number of stops and is
  deliberately out of scope here.
* A real traffic feed would replace the JSON file; the FIFO validation and the
  solver contract stay unchanged.

## Rejected alternatives

* **Time-expanded graph.** Correct for any profile, but multiplies the graph by
  the number of time slices and loses the clean path materialisation. With a
  validated FIFO profile, time-dependent Dijkstra is simpler and exact.
* **Piecewise-constant multipliers.** The 13:00 boundary alone breaks FIFO on
  any edge longer than the boundary's time drop; interpolation is the fix.
* **Per-class profiles now.** Requires a graph schema change and a rebuild of
  both artifacts for a synthetic profile. Recorded as future work in the
  roadmap, not smuggled in.
