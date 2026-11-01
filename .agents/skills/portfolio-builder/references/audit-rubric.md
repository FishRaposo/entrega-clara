# Audit rubric

Two time-boxed tests and a severity table. Run the mechanical audit first
(`scripts/portfolio_audit.py`), then this.

## The 60-second test

Open the repository in a private window, as a recruiter would.

- [ ] The repository card has a description that says what it is, topics, and a homepage/live URL.
- [ ] The README first screen says what it is, why it exists, what it proves, how to see it.
- [ ] One visual is visible without scrolling far.
- [ ] The default branch is green (or the badge is absent, not red).
- [ ] A live/replayable demo link is in the first screen.
- [ ] A license is present.

Any miss is a blocker: a reviewer who leaves at 60 seconds never sees the depth.

## The 10-minute test

As a hiring manager.

- [ ] The demo opens without installing anything, or the clone-and-run path is three commands.
- [ ] One deep artifact is readable in five minutes (benchmark table, ADR, verification record).
- [ ] The claims table links to the tests or artifacts that prove them.
- [ ] Real vs simulated is stated; limits are explicit.
- [ ] Tests exist and are relevant, not just smoke.
- [ ] The commit history is legible (messages describe intent; authorship is deliberate).

## Severity table

| Severity | Finding | Fix |
| --- | --- | --- |
| Blocker | Red CI on the default branch | Diagnose the failing job; fix the cause; never skip the gate |
| Blocker | No live, static or recorded demo | Add the cheapest evaluable artifact (hosted demo, static replay, 30–60 s video) |
| Blocker | Empty repo description / no topics / no homepage | Fill the repo card (`assets/repo-card.md`) |
| Blocker | Claims with no artifact | Measure, soften to what is true, or delete |
| Major | Stale docs contradicting the code | Truth pass: endpoints, commands, counts, statuses |
| Major | README opens with the stack or installation | Rewrite the first screen around what/why/proof/see |
| Major | Optional infrastructure required to see the demo | Make it opt-in; ship a memory/offline default |
| Major | Real vs simulated not stated | Add the two-column table and the not-built list |
| Major | Stale screenshots or benchmarks | Regenerate; gate freshness in CI |
| Minor | No license, no attribution | Add both |
| Minor | No media, or media over budget | Compress, link large media |
| Minor | Dense, uniform typography; no captions | One idea per screen, captions that explain |
| Minor | Commit messages like "fix", "wip" | Squash or rewrite the visible history if the repo is the portfolio |

## Claim-to-artifact procedure

1. Extract every sentence with a number, comparison or guarantee.
2. For each: artifact path and the command that regenerates it.
3. Missing artifact → measure, soften, or remove.
4. Add the surviving rows to the reviewer page's claims table.

## Stale-document sweep

Search the docs for: `planned`, `coming soon`, `not implemented`, `future`, `deferred`,
`production-ready`, `TODO`, and any count of tests, endpoints or files. For each hit, decide: true
today, historical (label it), or wrong (fix it). Regenerate committed artifacts and compare.

## CI failure playbook

The four classes found in practice, all fixable without weakening the gate:

- **Runner-label drift.** `ubuntu-latest` moved to a distribution the pinned browser toolchain does
  not support. Pin the runner (`ubuntu-24.04`) or upgrade the toolchain; add a comment with the
  unpin condition.
- **Optional dependency missing in CI.** A type checker or test imports an optional adapter. Put its
  drivers in the development extra, or make the import lazy with a clear error.
- **Import at collection time.** A test loads a module by path without registering it in
  `sys.modules` (Python 3.11 dataclasses resolve annotations through it), or a helper imports an
  optional library at module scope. Register the module, or move the import inside the function.
- **Whitespace gate over cumulative history.** Markdown hard breaks (two trailing spaces) fail
  `git diff --check root..HEAD`. Strip them; the gate compares trees, not commits, so fixing the
  working tree is enough.

## Repo card audit

| Field | Standard |
| --- | --- |
| Description | One sentence: what it is + who it is for + one proof point; under ~160 characters |
| Topics | 6–10: domain, stack, techniques, data source; no jokes |
| Homepage | Live demo or docs URL; never empty when a demo exists |
| Social preview | 1280×640 image with the project name and one number |
| License | Present and correct |
| Pinned | The repository is pinned on the profile |

The rubric is derived from direct audits and practitioner guidance, not a validated survey; treat it
as a checklist, not a measurement.
