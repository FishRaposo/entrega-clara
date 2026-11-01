# ADR 0009 — City-scale graph and contraction hierarchies

Status: accepted. Implemented by `scripts/data/osm_pbf.py`,
`scripts/data/build_city_graph.py`, `routing/contraction.py`,
`routing/ch.py` and the city benchmark artifact
(`docs/benchmarks/routing-city.{json,md,svg}`).

Companion decision: [ADR 0008](0008-real-street-graph-and-landmarks.md) chose the
real extract and ALT, and explicitly deferred contraction hierarchies "at this
scale… revisit if the extract grows by an order of magnitude". It grew by 44×.

## Context

The centro graph proved the ladder but not the scale. Every number came from
2,405 nodes, where a Dijkstra answers in about a millisecond and the
asymptotics are invisible. A reviewer cannot tell whether the design survives a
real city, and the project's own selection story ("use the right solver for the
problem") was untestable without a graph where the rungs differ by orders of
magnitude.

Two constraints shaped the decision:

* **No new runtime dependency.** Reading a regional OpenStreetMap extract must
  not pull in protobuf, pyrosm or osmnx.
* **Pure Python.** CPython is roughly two orders of magnitude slower than C++
  for graph preprocessing, so any algorithm chosen has to be cheap enough to
  build from source in this environment, not just in theory.

## Decision

1. **Read PBF with the standard library.** `scripts/data/osm_pbf.py` implements
   the protobuf wire format (varints, length-delimited fields, zlib blobs) and
   the OSM schema subset that matters: dense and plain nodes, delta-coded ways,
   the tag indices for four road keys. It streams two passes (bbox nodes, then
   ways), splits ways that leave and re-enter the box into contiguous segments,
   and rejects unsupported features (`HistoricalInformation`,
   `LocationsOnWays`) loudly instead of misreading them. Tested against a
   writer built in the test file, so no binary fixture is committed.
2. **Build the city graph with the same rules as the demo graph.** The
   municipality bbox, the highway whitelist, oneway and `maxspeed`, distances
   ceiled to 0.1 m *after* rounding coordinates, degree-2 contraction, largest
   strongly connected component with the self-check, and one extra step that
   only matters at this scale: **drop nodes no road touches** (the node pass
   sees buildings, POIs and benches too — 14.4M nodes in the box, 1.04M on a
   road, 548k after contracting chains). Artifact:
   `data/graph/sao-paulo-city.json.gz`, **104,991 nodes / 177,114 directed
   edges, 2.1 MB gzipped** in the compact-v1 format. The largest strongly
   connected component holds about 10% of the contracted street junctions —
   one-way São Paulo fragments far more than the centro extract suggested.
3. **Implement contraction hierarchies** (`routing/contraction.py`):
   * edge-difference ordering computed **without** witness searches — ordering
     affects the shortcut count, not correctness, and a full witness pass per
     queue probe dominated preprocessing in pure Python;
   * hop-bounded witness search (3 hops, 200 settles) at contraction time; a
     missed witness only adds a redundant shortcut;
   * every shortcut stores its two child edges, so any query path expands back
     into original graph nodes;
   * queries run two upward Dijkstras with the standard `min(top) ≥ best`
     stopping rule and keep only the nodes they touch — array-per-query
     allocation dominated query time at 105k nodes.
4. **CH is the lab/benchmark solver of record, not the product default.** The
   product plans one route at a time and cannot amortize preprocessing; the
   selection guide publishes the break-even instead of asserting a winner.
5. **Measure preprocessing without profiling overhead.** The first benchmark
   run recorded 12.1 s because `tracemalloc` was active during preprocessing;
   the honest figure is 2.2 s. The artifact reports the bare build time and the
   shortcut count, not a memory number distorted by instrumentation.

## Measured results (committed artifact, 200 sampled pairs, time objective)

| Solver | Median nodes expanded | Share of graph | Median query time |
| --- | --- | --- | --- |
| Dijkstra | 53,885 | 51.3% | 122.8 ms |
| A* (straight line) | 44,759 | 42.6% | 166.1 ms |
| ALT (8 landmarks) | 6,186 | 5.9% | 64.1 ms |
| Bidirectional + ALT | 19,272 | 18.4% | 435.4 ms |
| **CH** | **85** | **0.1%** | **2.04 ms** |
| Weighted ε = 5 | 14,470 | 13.8% | 45.4 ms (max 13% over) |

* CH preprocessing on this graph: **2.2 s**, 164,517 shortcuts (0.93× the edge
  count), 3-hop witnesses.
* Break-even: **13 queries against A\*, 35 against ALT**. A dispatcher
  answering thousands of routes per minute amortizes the build immediately; a
  single route per process never does.
* The straight-line heuristic is weak on one-way streets: A* expands 17% fewer
  nodes than Dijkstra but takes 35% longer in wall time, because the heuristic
  costs more than the saved expansions. ALT is the first rung that actually
  moves the needle.
* Batch planning at city scale costs **~1.7 s** (one-to-all Dijkstra per stop,
  seven stops). That is a real bound on the current dispatch design and the
  motivation for pricing matrices with CH or a bounded corridor later.

## Why not a bigger graph, and why not CH everywhere

* The bbox is the municipality. Going wider adds mostly rural and duplicate
  connectivity without changing the solver story; the artifact budget (25 MB
  gzipped) and the SCC filter push in the same direction.
* CH preprocessing cost depends on graph **structure**, not just size: the
  uniform synthetic lattice was pathological (more than 10 minutes at 40k
  nodes, because every witness search explores a broad, symmetric frontier),
  while the one-way-dominant OSM graph contracts 105k nodes in about two
  seconds. The ADR records the shape of the data, because a reader benchmarking
  CH on a grid would draw the wrong conclusion.
* The product keeps the centro graph: 12k-node reads, 1 ms routes and a
  browser-renderable lab do not need a city artifact.

## Consequences

* Work-bound tests now exist at both scales: city CH must stay under 1% of the
  graph and under 3× the edge count in shortcuts; exactness is asserted against
  the Dijkstra oracle on sampled city pairs.
* `docs/architecture/solver-selection.md` becomes the decision record that ties
  the measurements to a choice, with CH's break-even as the pivot.
* The batch matrix cost is measured and reported rather than assumed cheap.
* Regenerating the city artifact requires a regional PBF (Geofabrik) and about
  fifteen minutes; the build step is documented and the output is committed, so
  the runtime never needs network access.
