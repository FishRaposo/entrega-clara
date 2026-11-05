# Audit rubric

Two time-boxed tests and a severity table. Run the mechanical audit first
(`scripts/portfolio_audit.py . --remote --network --demo-contract --claims`), then this. The script
checks presence, reachability, the demo contract and CI status; `--claims` lists the numbers, but only
you can decide whether each is still true.

**Scope:** public, recruiter-facing repositories only. Private repositories and hubs/collections are
out of scope; the mechanical audit returns `SKIP` and stops. Do not apply these tests to them.
Without `--remote`, privacy is unverified and the audit warns. Use `--fail-on-skip` in CI so an
out-of-scope repository does not pass silently.

## The 60-second test

Open the repository in a private window, as a recruiter would.

- [ ] The repository card has a description that says what it is, topics, and a homepage/live URL.
- [ ] The README first screen says what it is, why it exists, what it proves, how to see it.
- [ ] One visual is visible without scrolling far.
- [ ] The latest default-branch CI run is green; the badge, if present, matches it.
- [ ] A live/replayable demo link is in the first screen and resolves.
- [ ] The demo is more than a screenshot: it names the project, shows one real artifact and offers one
      control that produces a visible result.
- [ ] The demo returns to the source repository and the portfolio/profile.
- [ ] A license is present.

Any miss is a blocker: a reviewer who leaves at 60 seconds never sees the depth.

## The 10-minute test

As a hiring manager.

- [ ] The demo opens without installing anything, or the clone-and-run path is three commands.
- [ ] The demo maps to the repository: the input, the process and the output are traceable to real code
      or committed artifacts.
- [ ] A concept demo is labeled, says what is simulated, and links the real repository and portfolio.
- [ ] The demo has a provenance marker and no direct remote API call.
- [ ] One deep artifact is readable in five minutes (benchmark table, ADR, verification record).
- [ ] The claims table links to the tests or artifacts that prove them.
- [ ] Real vs simulated is stated; limits are explicit.
- [ ] Tests exist and are relevant, not just smoke.
- [ ] The commit history is legible (messages describe intent; authorship is deliberate).
- [ ] If clients are an audience, a problem → scope → outcome → proof block exists.

## The demo contract

The `--demo-contract` check is a floor. It fetches the demo page and requires a source-repository link,
then checks for a portfolio/profile link, a provenance marker, a static/concept label, an interactive or
visual artifact, and no direct remote API call. A missing repository link is a failure; the rest are
warnings that must be fixed or explained before the 60-second test. The contract cannot tell whether
the artifact is convincing, so the manual test still decides.

## Severity table

| Severity | Finding | Fix |
| --- | --- | --- |
| Blocker | Red, cancelled or missing CI on the default branch | Diagnose the failing job or add the workflow; never skip the gate |
| Blocker | No demo | Add the demo or concept demo; use a recording only when interaction cannot be shown |
| Blocker | Hosted demo link returns 4xx/5xx | Fix the URL or the deploy; `--network` probes it |
| Blocker | Demo is a 200 error page, empty shell or login/back-end wall | Fix the page or the deploy; a demo must show the concept |
| Blocker | Demo has no source-repository return link | Add the repo link; `--demo-contract` fails without it |
| Major | Demo has no portfolio/profile return link | Add the profile or portfolio path; the index itself remains out of scope |
| Major | The profile never pins or names the piece | Pin it or list it; the demo's portfolio link dead-ends |
| Major | Demo is only a screenshot or static landing page | Add a real artifact and one working control |
| Major | Concept demo is unlabeled, invents metrics or pretends to be the deployed product | Label the simulation, use committed real data and link the repository |
| Major | Demo requires a backend, login, Docker or an install | Move the front door to a static concept demo; host the real app separately |
| Major | Demo makes a direct remote API call while claiming to be static | Remove it or relabel the demo as a hosted app |
| Major | The same shell with a swapped artifact across unrelated pieces | Change the composition; the contract is shared, the layout is not |
| Major | Demo is stale or uses data no longer in the repository | Regenerate the demo data with the feature change |
| Minor | Demo has no provenance marker | Link the source path, trace, benchmark or commit |
| Blocker | Empty repo description / no topics / no homepage | Fill the repo card (`assets/repo-card.md`) |
| Blocker | Claims with no artifact | Measure, soften to what is true, or delete |
| Blocker | Numbers contradicted by the committed artifact | Regenerate, then update every doc that repeats them |
| Major | Stale docs contradicting the code | Truth pass: endpoints, commands, counts, statuses |
| Major | Dirty tree or unpushed commits | Commit and push; reviewers see the pushed tree |
| Major | README opens with the stack or installation | Rewrite the first screen around what/why/proof/see |
| Major | Optional infrastructure required to see the demo | Make it opt-in; ship a memory/offline default |
| Major | Real vs simulated not stated | Add the two-column table and the not-built list |
| Major | Stale screenshots or benchmarks | Regenerate; gate freshness in CI |
| Minor | No license, no attribution | Add both |
| Minor | No media, or media over budget | Compress, link large media |
| Minor | No 1280×640 social-preview asset | Commit the image; upload is Settings-only |
| Minor | Dense, uniform typography; no captions | One idea per screen, captions that explain |
| Minor | Commit messages like "fix", "wip" | Squash or rewrite the visible history if the repo is the portfolio |

## Claim-to-artifact procedure

1. Run `--claims`; take every line it lists, plus any sentence with a comparison or guarantee.
2. For each: artifact path and the command that regenerates it.
3. Missing artifact → measure, soften, or remove.
4. Check the artifact's `commit` stamp: `-dirty` or a hash outside the published history is a
   provenance warning. Regenerate from a clean tree or state the caveat.
5. Add the surviving rows to the reviewer page's claims table.

## Stale-document sweep

Search the docs for: `planned`, `coming soon`, `not implemented`, `future`, `deferred`,
`production-ready`, `TODO`, `nothing is deployed`, `not deployed`, `enabling Pages`, and any count of
tests, endpoints or files. For each hit, decide: true today, historical (label it), or wrong (fix it).
Regenerate committed artifacts and compare, including their `commit` stamps: a `-dirty` suffix or a
hash outside the published history is a provenance warning.

Run a repo-wide link check over every markdown file, not just the five the script scans, and probe the
external URLs too: `--network` probes the demo URL only, so dead citations survive a green audit.
Template placeholders (for example a literal `<path>`) and URL-encoded filenames are false positives.

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
| Social preview | 1280×640 image; commit the asset and upload it; `--remote` warns until GitHub reports a custom preview |
| Return path | the profile pins or names the repository; a demo link into a profile that omits the piece is a dead end |
| License | Present and correct |
| Pinned | The repository is pinned on the profile |

The rubric is derived from direct audits and practitioner guidance, not a validated survey; treat it
as a checklist, not a measurement.
