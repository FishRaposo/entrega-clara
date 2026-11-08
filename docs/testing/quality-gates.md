# Quality gates

The repository uses deterministic root-level checks to keep the lunch-rush seed,
requirements traceability, and `app/` source boundary trustworthy.

| Gate | Direct command |
| --- | --- |
| Seed validation | `python scripts/data/validate_seed.py data/scenarios/lunch-rush.json` |
| Requirement coverage | `python scripts/quality/check_requirement_coverage.py docs/requirements/traceability.md` |
| Application boundary | `python scripts/repo/check_app_boundary.py` |
| Routing benchmark smoke | `python scripts/bench/routing_benchmark.py --smoke` |

`validate_seed.py` checks the complete lunch-rush entity/event schema, rejects
secret-like fields, and dry-runs every transition without mutating seed data.

`check_requirement_coverage.py` requires RF01–RF14 and RNF01–RNF10 in the
traceability matrix. `check_app_boundary.py` inspects only files immediately at
the repository root; supported configuration and shell files remain allowed.

`routing_benchmark.py --smoke` loads the committed graph and asserts that
Held-Karp equals brute force on a small matrix and that ALT equals the Dijkstra
oracle on the graph — a one-second guard against a broken solver ladder. The
full harness regenerates `docs/benchmarks/` and is not part of CI.

## One command for the whole gate

`python scripts/check.py` runs, in order: seed validation, requirement coverage,
app boundary, ruff, mypy, pytest, web vitest, web lint, and web typecheck. It is
stdlib-only and works in PowerShell.

The check does not run the Next production build or Playwright; CI covers both
(`.github/workflows/ci.yml` builds the web app and runs the browser journeys,
including the axe scans).
CI also runs `git diff --check` across committed history and the benchmark smoke.
