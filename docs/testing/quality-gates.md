# Quality gates

The repository uses deterministic root-level checks to keep the lunch-rush seed,
requirements traceability, and `app/` source boundary trustworthy.

| Gate | Direct command | Make command |
| --- | --- | --- |
| Seed validation | `python scripts/data/validate_seed.py data/scenarios/lunch-rush.json` | `make seed-validate` |
| Requirement coverage | `python scripts/quality/check_requirement_coverage.py docs/requirements/traceability.md` | `make requirement-coverage` |
| Application boundary | `python scripts/repo/check_app_boundary.py` | `make app-boundary` |

`validate_seed.py` checks the complete lunch-rush entity/event schema, rejects
secret-like fields, and dry-runs every transition without mutating seed data.

`check_requirement_coverage.py` requires RF01–RF14 and RNF01–RNF10 in the
traceability matrix. `check_app_boundary.py` inspects only files immediately at
the repository root; supported configuration and shell files remain allowed.

CI also runs `git diff --check` across committed history. Run `make check` to
include the data gates with lint, typecheck, and test commands.
