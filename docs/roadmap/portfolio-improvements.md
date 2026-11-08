# Portfolio improvement plan

**Status:** ✅ Implemented — see ledger below (last updated 2026-10-31)
**Written:** 2026-10-31, from a review of the local working tree after the M1 vertical slice
**Related:** [platform evolution roadmap](platform-evolution.md), [routing contract](../architecture/routing-contract.md), [external dependencies](../architecture/external-dependencies.md)

> **Historical backlog.** This page records a past review. Items it calls deferred — contraction
> hierarchies, time windows and capacity, dynamic re-routing, the PostgreSQL adapter and the outbox —
> were delivered afterwards; see [ADR 0009](../adr/0009-city-scale-graph-and-contraction-hierarchies.md),
> [ADR 0011](../adr/0011-capacity-windows-and-dynamic-replanning.md),
> [ADR 0012](../adr/0012-postgres-adapter-outbox-and-metrics.md) and
> [the verification record](../verification.md).

This page lists what would make Entrega Clara a stronger portfolio piece, and how to build each item. It is a backlog, not a commitment: pick items in the suggested order at the end.

## Implementation ledger

| Item | Status | Evidence |
| --- | --- | --- |
| F1–F3 routing fixes | ✅ done | `domain/geo.py`, objective-aware A*, graph 1.0.1, `tests/routing/test_graph_solvers.py` |
| P1 time-optimal routing | ✅ done | `objective` param end-to-end, admissibility/consistency proofs |
| P2 multi-stop solvers | ✅ done | `routing/tsp.py` (Held-Karp/NN/2-opt), `matrix.py`, precedence-aware |
| P3 benchmark harness | ✅ done | `docs/benchmarks/routing.{json,md,svg}`, `--smoke` CI gate |
| P4 algorithm lab | ✅ done | `/api/v1/lab/*` + `/lab` page, e2e-covered |
| P5 graph CLI | ✅ done | `build_graph.py --rows/--cols/--seed/--out` |
| R1 screenshots | ✅ done | `docs/media/*.png` via `e2e/screenshots.spec.ts` |
| R2 README first screen | ✅ done | recruiter section + media embeds |
| R3 verification record | ✅ done | `docs/verification.md` exact counts |
| W1 check.py / W2 dev.py | ✅ done | `scripts/check.py` runs the full gate; the planned `--fast`/`--e2e` flags were not added because the browser suite has its own command. `scripts/dev.py` starts both servers. |
| W3 Makefile | ✅ done | `dev` de-Dockered |
| W4 CI matrix | ✅ done | ubuntu+windows backend, e2e job, benchmark smoke |
| O1 ops timeline/ETA | ✅ done | `GET /operations/timeline` + panel table |
| O2 route-following GPS | ✅ done | `courier.route_step`, polyline-constrained pings |
| O3 snapshots | ✅ done | named in-memory + JSON export/import roundtrip |
| O4 courier batching | ✅ done | `POST /courier/batches/accept`, ADR 0007, cross-restaurant |
| Rate + cancel | ✅ done | `/me/orders/{id}/rate|cancel`, e2e covers rating |
| Real street graph | ✅ done | `scripts/data/fetch_osm_graph.py`, `data/graph/sao-paulo-centro-osm.json` (OSM, ODbL), ADR 0008 |
| ALT landmarks + bidirectional + weighted A* | ✅ done | `routing/landmarks.py`, `routing/informed.py`, differential tests on both graphs |
| Animated solver lab | ✅ done | `components/lab-canvas.tsx` + canvas `algorithm-lab.tsx`, `/lab` in the axe loop |
| Search replay GIF (stdlib renderer) | ✅ done | `scripts/media/render_search_gif.py` → `docs/media/lab-alt-vs-dijkstra.gif` |
| Pathfinding-first README | ✅ done | pitch, replay, chart, screenshots, built-vs-deferred table, origin story |
| Batch optimization payoff | ✅ done | `RoutePlan.baseline_*`, courier console line (Held-Karp vs nearest-neighbor) |
| R4 origin story | ✅ done | "Origem / Origin" in the README plus [docs/origin.md](../origin.md): two assignments merged, brute force kept as the legacy router, portfolio layer, iFood chronology |
| W5 housekeeping leftovers | ✅ done | local leftovers fixed; the remaining `httpx` TestClient deprecation warning comes from Starlette/FastAPI upstream |

## Where the project stands

The repo now answers its origin question with measured evidence. A college
brute-force TSP that dies at ten stops is retained as the baseline, and the
ladder that replaces it — nearest neighbor, 2-opt, Held-Karp with precedence,
plus Dijkstra, A*, ALT landmarks, balanced bidirectional search and weighted
ε-A* for point-to-point routing — runs on **real OpenStreetMap streets of
central São Paulo** and is measured in `docs/benchmarks/`.

What a reviewer sees quickly:

1. `docs/media/lab-alt-vs-dijkstra.gif` — the same delivery route searched by
   ALT (70 expansions) and Dijkstra (167), replayed and drawn by a
   standard-library renderer.
2. `docs/benchmarks/routing.md` — the ladder on one table, with the quality
   overshoot of the inexact variant and the one-time preprocessing cost.
3. The courier console showing a batch tour computed by Held-Karp next to what
   nearest-neighbor would have cost.

What a reviewer still cannot see: a hosted demo, a durable database adapter,
real providers, or a graph larger than one city district.

## Constraints every item respects

- **Toolchain:** Python 3.11+ and Node 22+ only. No Docker, no WSL, no database, no `make` required, no provider accounts.
- **Windows is a first-class host.** Every command must run in PowerShell.
- **No new runtime or dev dependencies.** Everything below the "Future maybe" section uses the Python standard library, the packages already in `pyproject.toml` / `package.json`, or tools already installed (Playwright).
- **New dependencies are listed only under [Future maybe](#future-maybe-new-dependencies),** each with what it would unlock.
- **Honest claims.** Nothing gets described as done, measured or production-grade until a test or a committed result shows it.

## Where the project stood before this round

The M1 slice was real and well built: catalog, cart, coupons, idempotent
checkout with simulated payment, restaurant and courier commands with business
invariants, post-commit events, authorized SSE, an operations read model, four
pt-BR role surfaces, a guided lunch-rush replay through the same handlers, and
Playwright journeys with axe scans.

What a reviewer could not see in five minutes:

1. **The graph was fictional.** Every distance, ETA and benchmark number came
   from a 77-node synthetic lattice.
2. **The solver ladder stopped at A*.** No landmarks, no bidirectional search,
   no measured quality/work trade-off.
3. **The lab was static.** Expanded-node sets were drawn as fixed circles; a
   real-size graph could not be rendered at all.
4. **Nothing showed the search moving**, and no screenshot or chart put a
   number on the algorithms.

Items 1–4 are addressed above; the sections below keep the original review
findings and implementation notes for history.

## Findings from the review

These were checked against `data/graph/sao-paulo-centro.json` (graph 1.0.0, 77 nodes, 302 directed edges) with a standalone script that reimplements the same edge weights. Item P1 turns each into a committed test.

### F1. The live route is the shortest, not the fastest

`AStarPathSolver` minimizes `distance_meters`, but the graph has 40 km/h avenue corridors and 25 km/h streets, and the ETA shown to the customer is computed from edge speeds.

- For **3,583 of 5,852 node pairs (61%)**, the shortest-distance path is slower than the fastest path available.
- In the worst pair the chosen route takes **60% longer** than the fastest one.

So the courier is sent on a route that is not time-optimal, and the displayed ETA is the ETA of a suboptimal route. This is the most valuable fix in the list: it's a real routing insight, and it makes a good paragraph in any write-up.

### F2. The A\* heuristic is admissible only approximately

`scripts/data/build_graph.py` rounds each edge length with `round(..., 1)`. For **20 of 302 edges**, the stored length ends up shorter than the straight-line (haversine) distance, by at most 1 mm. The haversine heuristic can therefore overestimate by a hair, which formally breaks admissibility. In practice the current oracle test passes because it compares with `abs=0.01`. The fix is one line and a test, and it shows rigor.

### F3. A layering inversion in routing

`routing/graph.py` and `routing/path.py` import `haversine_m` from `adapters/memory/routing.py`, and `graph.py` does it inside a function to dodge a circular import. Domain/routing code should not depend on an adapter.

### F4. Windows and no-Docker drift

- `Makefile` `dev` still runs `docker compose up --build`.
- `Makefile` `test` uses POSIX `PYTHONPATH=... python ...`, which fails in PowerShell and cmd.
- `.env.example` sets `DATABASE_URL` to the Docker host `db`.
- `app/web/test-results/` exists locally and is not in `.gitignore`.

### F5. Documentation drift

- README "Release and publication status" still says "This scaffold".
- README says "~140 testes"; an approximate count undercuts the "verifiable quality" bullet next to it.
- `docs/architecture/external-dependencies.md` "Optional configuration" has a table header with no rows, so it renders broken.
- `docs/roadmap/platform-evolution.md` M1.0 and M1.5 still list SQLAlchemy/Alembic and the MapLibre adapter as M1 scope, and the M1 definition of done still requires "Memory and PostgreSQL adapters". The PostgreSQL re-entry note explains the deferral, but the table and checklist should say so inline.
- `docs/requirements/traceability.md` "Scaffold verification status" predates M1.
- `docs/README.md` does not link `external-dependencies.md`.
- `adapters/memory/routing.py` docstring still says "Phase 4 replaces this adapter"; it is now the fallback planner.

---

## P. Routing: the original question (highest value)

### P1. Route on travel time, with an exact heuristic

**Why:** fixes F1 and F2; the product claims an ETA, so the route should minimize time.

**How:**

1. In `routing/path.py`, add `objective: Literal["time", "distance"] = "time"` to `PathProblem`.
2. Add one weight function used by both solvers:
   - `distance` → `edge.distance_meters`
   - `time` → `edge.seconds`
3. A\* heuristic per objective:
   - `distance` → `haversine_m(node, goal)`
   - `time` → `haversine_m(node, goal) / graph.max_speed_mps`, where `max_speed_mps` is computed once in `load_graph` from the fastest edge. Dividing by the fastest possible speed keeps it admissible.
4. Add `objective` to `PathResult`, `DeliveryRouteResult` and `RoutePlan`, bump `solver_version` to `2.0.0`, and show the objective in the map caption ("mais rápida").
5. `GraphRoutePlanner` uses `objective="time"`.
6. In `build_graph.py`, replace `round(distance, 1)` with `math.ceil(distance * 10) / 10` so every edge is at least its straight-line length, then regenerate as graph version `1.0.1`.
7. Move `haversine_m` to a new `domain/geo.py` and import it from there in both routing and the adapter (fixes F3).

**Tests to add (`tests/routing/test_graph_solvers.py`):**

- A\* equals Dijkstra on cost for 150 seeded pairs, **for both objectives**.
- Admissibility: for every node and goal, `h(node) <= true cost` (77 × 77 is cheap).
- Consistency: for every edge `(u, v)`, `h(u) <= w(u, v) + h(v)`, for both objectives.
- Every stored edge length is at least the haversine distance between its endpoints.
- One pinned node pair where the distance-optimal and time-optimal paths differ, asserting the time path is faster.

**Done when:** the live courier route minimizes time, the five tests pass, and the routing contract doc states the objective.

### P2. Multi-stop solvers: answer "what replaces brute force"

**Why:** this is the project's origin. The matrix contract (`RouteProblem`, `RouteResult`, `RouteSolver`) and the legacy solver already exist; the replacements don't.

**How (new module `routing/tsp.py`, standard library only):**

| Solver | Idea | Practical range | Guarantee |
| --- | --- | --- | --- |
| `LegacyBruteForceTSPSolver` (exists) | try every order, O(n!) | ~10 stops | exact |
| `HeldKarpSolver` | bitmask dynamic programming, O(n²·2ⁿ) time, O(n·2ⁿ) memory | ~16–18 stops | exact |
| `NearestNeighborSolver` | always go to the closest unvisited stop | thousands | none (a fast first guess) |
| `TwoOptSolver` | start from nearest neighbor, reverse segments while it shortens the tour | thousands | local optimum; gap measured in P3 |

Implementation notes:

- All four implement the existing `RouteSolver` protocol and return `RouteResult`. Keep `routes_evaluated` as the work counter and document what it counts per solver (permutations, DP states, or 2-opt moves).
- Add hard input caps that raise a typed error: brute force above 11 stops, Held-Karp above 18. The roadmap already forbids unbounded factorial work in a request.
- **Building the cost matrix from the street graph:** add `build_cost_matrix(graph, stop_nodes, objective)` in `routing/matrix.py`. Run Dijkstra **one-to-all** from each stop (n runs) instead of A\* for every pair (n² runs). This is a nice teaching point: A\* wins for one destination, Dijkstra wins when you need all of them.
- Stretch: pickup-before-drop-off precedence. In Held-Karp, skip a state transition that visits a drop-off before its pickup; in 2-opt, reject moves that break precedence.

**Tests (`tests/routing/test_tsp.py`):**

- Held-Karp cost equals brute-force cost for n = 3…8 on seeded random matrices.
- Every solver returns a valid closed tour: starts and ends at the origin and visits each stop exactly once.
- 2-opt cost is less than or equal to nearest-neighbor cost on the same input.
- 2-opt cost is greater than or equal to the exact optimum (sanity check).
- The caps raise the typed error.
- `build_cost_matrix` agrees with pairwise A\* results.

**Done when:** all solvers are behind one contract and tested against the exact ones.

### P3. Benchmark harness and committed results

**Why:** turns "unusable after about 10 stops" into a measured chart, and gives the README and any article a headline exhibit.

**How (new `scripts/bench/routing_bench.py`, standard library only):**

1. Seeded random stop sets drawn from the graph (or random symmetric matrices for large n).
2. Sizes:
   - brute force: 4…11
   - Held-Karp: 4…18
   - nearest neighbor and 2-opt: 4…500
3. Repeat each size 5 times and record the median of `time.perf_counter_ns()`. Also record the optimality gap of the heuristics against Held-Karp wherever Held-Karp can run.
4. Pathfinding section: A\* vs Dijkstra on the same 150 pairs, with median nodes expanded and median time, for both objectives.
5. Write `docs/benchmarks/routing-<date>.json` and a matching `.md` table, including the machine context: `platform.platform()`, `platform.processor()`, the Python version and the git commit (via `subprocess`, if git exists).
6. Draw the chart as **hand-written SVG** from Python, with no plotting library: runtime vs stops, log-scale y axis, one line per solver. Save `docs/benchmarks/routing-scaling.svg` and embed it in the README. About 80 lines of code.
7. Add `--smoke` (tiny sizes, about 2 seconds) for CI.

**Honesty rule:** label measured points and extrapolated points differently. If brute force is not run at 12+, say so; don't plot it.

**Done when:** one command regenerates the JSON, the table and the SVG, and the README shows the chart.

### P4. Show the search: an algorithm lab page

**Why:** one picture of A\* exploring fewer nodes than Dijkstra explains the algorithm faster than any paragraph. It's also the best image for an X or LinkedIn post.

**How:**

1. Add an optional `trace=True` to both path solvers that records `expanded_order: tuple[str, ...]`. It is bounded by the graph size and off by default, so the courier flow pays nothing for it.
2. Add a read-only `GET /api/v1/lab/path?origin=&destination=&solver=astar|dijkstra&objective=time|distance` route in a new `api/routes/lab.py`. Validate that the nodes exist, expose no factorial solver over HTTP, and reuse the existing error envelope.
3. Optional: `GET /api/v1/lab/benchmarks` serving the latest committed benchmark JSON.
4. Add a `/lab` web page (`app/web/src/app/lab/page.tsx` and `components/algorithm-lab.tsx`):
   - Reuse the projection logic from `delivery-map.tsx`. Extract it to `lib/projection.ts` first so both components share it.
   - Draw expanded nodes as gray dots, the final path in color, and Dijkstra and A\* side by side, each showing its count of expanded nodes.
   - Add controls for origin, destination and objective (the time vs distance toggle visualizes F1).
   - Draw the benchmark chart from the JSON as inline SVG with no chart library.
5. Add `/lab` to the axe loop in `e2e/journeys.spec.ts` and to the role switcher.

**Done when:** the lab page loads offline, passes axe, and a vitest test covers the projection helper.

### P5. A larger graph for the lab and benchmarks

**Why:** on 77 nodes, A\* and Dijkstra barely differ and large stop counts don't fit. The demo graph should stay small; the lab needs a bigger one.

**How:**

1. Give `build_graph.py` command-line options with `argparse`: `--rows`, `--cols`, `--seed`, `--graph-id`, `--out`. Keep the current values as defaults, so the demo graph is unchanged.
2. Generate a larger graph (for example 40 × 40) **at benchmark time from its seed** instead of committing a file of about 1 MB. Commit only the results.
3. Optional: if `nearest_node` gets slow on larger graphs, add a simple grid-bucket index in `routing/graph.py`. It is O(n) today, which is fine at 77 nodes.

---

## R. Reviewer experience: the five-minute test

### R1. Screenshots generated by the existing Playwright setup

**How:** add `app/web/e2e/screenshots.spec.ts`, tagged `@screens`, that walks the same journey and calls `page.screenshot({ path: "../../docs/media/<name>.png" })` for:

- customer tracking with the map
- restaurant queue
- courier console
- operations panel
- the lab (after P4)

Run it with `npx playwright test --grep @screens`, commit the PNGs, and exclude the spec from the default run with `grepInvert` in the config. Playwright can also record video natively (`video: "on"`), which gives a `.webm` demo clip with no new dependency.

### R2. README first screen

Reorder the top of `README.md` so the first screen holds:

1. One-line pitch.
2. Two screenshots: customer tracking and the lab.
3. A **built vs deferred** table (checkout, routing, SSE, roles, lab: built; Postgres, real payments, real auth, MapLibre, notifications: deferred).
4. Three headline numbers taken from the verification record (R3): tests passing, routing objective, benchmark headline.
5. "Run it in 4 commands" (already present; keep it).

Then fix the drift from F5: replace "This scaffold" and replace "~140 testes" with the exact counts from R3.

### R3. Verification record

Add `docs/verification.md`, matching the format of the other portfolio repos:

- date, commit SHA, OS (Windows 11), Python and Node versions;
- each gate command with its **exact** result (for example "pytest: N passed", "vitest: N passed", "playwright: 2 passed", ruff, mypy, tsc, `next build`);
- what was not run and why (PostgreSQL, Docker, real providers);
- known limits (synthetic graph, simulated GPS and payments, single process).

Update it whenever the counts change. `scripts/check.py` (W1) can print the summary in this format.

### R4. Origin story section

Add a short "Origem / Origin" section, in pt-BR and English, that is factual and dated: an ADS class in October 2026 showed brute-force routing; it becomes unusable at around 10 stops; this repo is the follow-up. Link to the benchmark chart. One paragraph each.

---

## W. Windows-first tooling and consistency

### W1. `scripts/check.py`: one command for the full gate

A standard-library script that runs, in order: seed validation, requirement coverage, app boundary, pytest, ruff, mypy, web lint, typecheck, vitest and `next build`. Then it prints a pass/fail table with counts parsed from each tool's output.

- `--fast` skips the build.
- `--e2e` adds Playwright.

Point the README, `docs/testing/quality-gates.md` and the Makefile `check` target at it.

### W2. `scripts/dev.py`: start both servers with one command

Uses `subprocess.Popen` to start `python -m uvicorn delivery_platform.api.main:create_app --factory --port 8000` and `npm run dev` (`npm.cmd` on Windows, chosen through `shutil.which`). It prefixes each line with `[api]` or `[web]`, and Ctrl+C stops both (on Windows, start the children with `CREATE_NEW_PROCESS_GROUP` and terminate them in a `finally` block). Replace the Makefile `dev` target with `python scripts/dev.py`.

### W3. Makefile cleanup

- `test`: drop the `PYTHONPATH=` prefix. `pyproject.toml` already sets `pythonpath = ["src"]`; confirm the root `pytest.ini` resolves the same way.
- `dev`: call `scripts/dev.py` (W2).
- Keep the Makefile as optional aliases, as the README already says.

### W4. CI that proves the claims

In `.github/workflows/ci.yml`:

- Run the backend job on a matrix of `ubuntu-latest` and `windows-latest`. That proves the "Python + Node only, works on Windows" claim. Use `shell: bash` or split the whitespace check, which uses POSIX `$(...)`.
- Add an `e2e` job on Ubuntu: `npx playwright install --with-deps chromium`, then `npx playwright test`, uploading the Playwright report as an artifact on failure. The browser download is CI-side tooling, not a project dependency.
- Add `python scripts/bench/routing_bench.py --smoke` after P3.

### W5. Housekeeping

- `.gitignore`: add `test-results/` and `playwright-report/`.
- `.env.example`: comment out `DATABASE_URL` and say it is reserved for the future PostgreSQL adapter.
- Docker files: keep them, but add a one-line comment at the top of each saying "future container path, not used by the local run".
- Fix every item in F5.

---

## O. Product depth: make "measurable" real

### O1. Order timeline and ETA accuracy in operations

From the committed domain events, compute per-order stage durations (placed → confirmed → ready → picked up → delivered) and **ETA vs actual** (the route's `estimated_seconds` against the deterministic clock).

- Add it as a read model in `application/queries.py` and expose it through the existing operations route.
- Render it in `operations-panel.tsx` as a table.
- Test it against the lunch-rush scenario so the numbers are deterministic.

This is the portfolio thesis ("visible, measurable") made literal.

### O2. GPS that follows the route

Add a simulator that interpolates positions along the route's `node_path` at each edge's speed, ticking on the deterministic clock. The demo's `courier.location` steps and the courier console's "Enviar ponto GPS" button can then use the next simulated point, so the map marker moves along the street path instead of jumping between fixed coordinates.

Test: every point lies on a route segment, and timestamps increase monotonically (the existing invariant).

### O3. Snapshot export and restore (RNF09 evidence without a database)

Add `GET /api/v1/demo/snapshot` returning the memory store as JSON and `POST /api/v1/demo/snapshot` restoring it, both behind the demo identity. Test the round trip: export, mutate, restore, and compare. This gives backup and recovery evidence while PostgreSQL stays deferred.

### O4. Multi-stop delivery in the product (stretch, after P2)

Let operations batch two or three ready orders for one courier. The planner orders the stops with Held-Karp plus precedence, and the courier console shows the sequence. This relaxes the "one active delivery" invariant, so record the decision in `docs/adr/0007-multi-stop-batching.md` before building it.

---

## Future maybe: new dependencies

None of these are needed for anything above. Each would unlock something specific later.

| Dependency | Unlocks | Cost or caveat |
| --- | --- | --- |
| `maplibre-gl` + MapTiler free key | real map tiles behind the existing `DeliveryMap` props | browser-visible restricted key, attribution, quota |
| `hypothesis` | true property-based tests for solvers (shrinking counterexamples) | dev-only |
| `networkx` | an independent shortest-path and TSP oracle in tests | dev-only |
| `ortools` | an industrial reference solver to benchmark 2-opt against | large wheel |
| `matplotlib` | richer benchmark charts | not needed: P3 draws SVG by hand |
| `pytest-benchmark` | statistically careful micro-benchmarks | dev-only |
| `osmnx` / OpenStreetMap extract | real São Paulo streets instead of a lattice | ODbL attribution, bigger data, graph freshness |
| OSRM | real road routing service | needs Docker or a server; conflicts with the toolchain rule |
| `sqlalchemy` + `alembic` + `psycopg` + PostgreSQL | the deferred persistence adapter (ADR 0003) | needs Docker or a local Postgres install |
| `ffmpeg` | turning the Playwright `.webm` into a GIF | system tool |
| Hosting (Render or Fly for the API, Vercel for the web) | the API/web live demo | accounts; the static lab is already on GitHub Pages |

## Suggested order

| Step | Items | Rough effort | Result |
| --- | --- | --- | --- |
| 1 | P1 | half a day | correct, time-optimal routing with proofs |
| 2 | P2 | 1–2 days | the brute-force replacement exists |
| 3 | P3 | 1 day | the chart and measured numbers |
| 4 | R1–R4, W5, F5 fixes | 1 day | **portfolio-ready checkpoint** |
| 5 | P4, P5 | 1–2 days | the lab page |
| 6 | W1–W4 | 1 day | one-command dev and check, Windows CI |
| 7 | O1–O3 | 1–2 days | operations depth |
| 8 | O4 | later | multi-stop in the product |

After step 4, the repo answers its own origin question with measured evidence and can be sent with an application.
