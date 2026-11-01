# ADR 0008 — Real street graph and landmark-based acceleration

Status: accepted. Implemented by `scripts/data/fetch_osm_graph.py`,
`routing/landmarks.py`, `routing/informed.py` and the extended benchmark
harness; the sweep in `docs/benchmarks/routing.{json,md}` is the measured
evidence. The figures quoted below are the ones the decision was made on; the
current numbers live in the benchmark artifacts, and the solver ladder grew a
contraction hierarchy later ([ADR 0009](0009-city-scale-graph-and-contraction-hierarchies.md)).

## Context

Routing ran on a 77-node synthetic lattice. It was deterministic and
dependency-free, but it made every routing claim fictional: distances, ETAs,
map screenshots, batch tours and benchmarks all described a lattice nobody
drives. A portfolio piece whose subject is pathfinding cannot rest on a
toy graph, and its "A* expands fewer nodes" claim was not measurable at 77
nodes.

Real street data changes the problem in a way that is worth keeping visible:
**central São Paulo is a one-way network.** 76% of the ways in the extract
carry `oneway=yes`. A directed graph built honestly from that data has many
nodes you can enter but never leave, and the largest strongly connected
component holds only about a quarter of the junctions.

## Decision

1. **The product and the lab use a real OpenStreetMap extract** of central São
   Paulo (`data/graph/sao-paulo-centro-osm.json`), built offline by
   `scripts/data/fetch_osm_graph.py`: tiled Overpass queries (so one
   rate-limited sub-query cannot fail the run), raw tiles cached per area,
   standard library only, no runtime dependency and no network at run time.
   The synthetic lattice stays as the deterministic unit-test fixture and the
   offline fallback; `ROUTING_GRAPH_PATH` overrides the choice for both.
2. **Only the largest strongly connected component is kept.** Snapping a
   restaurant or address into a pocket the courier cannot leave would surface
   as `RouteUnavailableError` during a demo. Measured on the committed extract:
   16,816 raw nodes → 9,058 junctions after contracting degree-2 chains →
   2,405 in the largest component (26.6%). The builder proves the kept
   component is strongly connected before writing the file.
3. **Geometry is self-consistent**: coordinates are rounded to 6 decimals
   *before* any distance is measured, and distances are ceiled to 0.1 m, so
   every stored edge is at least the straight line between the stored
   coordinates. Without this the A* heuristic can overestimate by centimetres,
   which is exactly the admissibility bug this project documented in its first
   review round.
4. **ALT landmarks are the acceleration of record.** Eight landmarks by
   farthest-point selection, forward and reverse Dijkstra per landmark, a
   directed-graph triangle-inequality bound. Measured on 200 sampled pairs:
   median 352 expansions (14.6% of the graph) against 1,350 for Dijkstra
   (56.1%) and 815 for the straight-line A* (33.9%); preprocessing costs about
   37 ms once per (graph, objective) and is reported separately from query
   time. A* with a straight line stays the production solver because it needs
   no preprocessing; the lab and the benchmarks compare the rungs explicitly.
5. **Weighted ε-A* and bidirectional search are kept, labelled honestly.**
   Weighted A* is inadmissible by construction and the lab says so; its value
   is the measured quality/work trade-off (ε=1.5: −20% expansions, max 0.26%
   overshoot; ε=5: −58% expansions, max 59% overshoot). Bidirectional search
   is exact and expands 24.7% of the graph, but is currently *slower* in wall
   time than Dijkstra under CPython — two heaps plus two potential lookups per
   relaxation. The table reports that instead of hiding it.
6. **Contraction hierarchies are out of scope** at this scale. Preprocessing
   plus witness searches add a large surface of code that the differential
   test suite would have to pin down, for a graph that fits in 0.7 MB and
   answers in about a millisecond. Revisit if the extract grows by an order of
   magnitude.
7. **Cost matrices come from one-to-all Dijkstra per stop** (n runs) instead
   of A* for every ordered pair (n² runs). A* wins for one destination;
   Dijkstra wins when every destination is needed at once — a batch matrix
   asks for all of them. A pairwise-A* path stays behind the `solver`
   injection point so a test can prove both builders agree.

## Consequences

- OpenStreetMap attribution (ODbL 1.0) is part of the artifact: it is stored
  in the graph document, served by the lab, shown on the lab page and repeated
  in the README.
- The graph is a dated snapshot (`version: osm-<date>`). Regenerating it
  changes distances, ETAs and benchmark numbers, so the benchmark artifacts
  must be regenerated in the same change.
- Every routing artifact — screenshots, the animated replay, the benchmark
  tables — is tied to the committed extract; the screenshot spec is re-run
  whenever the graph or the lab changes.
- The one-way finding is now part of the product narrative: the courier
  console shows the computed one-way-aware tour, and the lab can explain why a
  straight-line heuristic is weak here and what landmarks buy.
- Dynamic re-optimization mid-route, capacity and time windows remain
  deferred; this ADR only fixes the data source and the acceleration policy.
