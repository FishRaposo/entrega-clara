# Portfolio sweep

The unit of review is the repository; the unit of hiring is the portfolio. Run the sweep when you need
to compare projects, prioritize fixes, or prepare a profile.

## Install once

The skill lives at the user level so every project can load it:

```bash
cp -r .agents/skills/portfolio-builder ~/.agents/skills/
```

PowerShell:

```powershell
Copy-Item -Recurse .agents\skills\portfolio-builder $HOME\.agents\skills\
```

## Run it

```bash
python ~/.agents/skills/portfolio-builder/scripts/portfolio_sweep.py ~/Projects \
  --depth 2 --remote --network --output ~/Projects/portfolio-audit.md
```

- `--depth 2` finds repositories one and two levels below the root; raise it for deeper layouts.
- Discovery stops at each repository root and skips `node_modules`, virtualenvs, build output and
  caches.
- `--remote` adds repo-card and default-branch CI checks through `gh`; `--network` probes demo URLs.
- `--strict` exits non-zero on warnings too, for a portfolio gate.
- The Markdown report lists every check per repository and a **Fix first** section.

The terminal output is a compact table; the report carries the details. Keep the report outside the
individual repositories — it is portfolio-level working state.

## Read it in this order

1. **Blockers across repositories.** Red CI, a broken demo, an empty card or contradicted numbers in
   any pinned repository outweighs a warning in five unpinned ones.
2. **The flagship.** Pick the repository that carries the thesis and fix its blockers first. The others
   support it; five equal projects read as none.
3. **Repo cards and consistency.** Description, topics, license, homepage and social preview should be
   present and consistent across the pinned set.
4. **Warnings by leverage.** A missing social preview is cheap; a stale benchmark is not.

## Portfolio-level decisions

- **Pin 3–6 repositories.** Each gets a distinct thesis; archive tutorial clones and forks with no
  changes.
- **Profile README.** One line per pinned repository: what it is, one proof point, link. It is the
  portfolio's first screen.
- **One flagship.** The strongest measured project leads; the rest show range, not competition.
- **Consistency.** Same license posture, same card fields, no repository that contradicts the
  flagship's quality.
- **Do not leave a red repository pinned.** Fix it, unpin it, or archive it.

## Boundaries

- The sweep is discovery and prioritization; it does not replace the 60-second and 10-minute tests on
  the flagship.
- Local checks are host-agnostic; `--remote` assumes GitHub (`gh`, Pages, repository metadata).
- The sweep imports the same audit functions as `portfolio_audit.py`; do not duplicate checks between
  the two scripts.
