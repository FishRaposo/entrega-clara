---
name: portfolio-builder
description: Turn a software project into a credible portfolio piece for recruiters, hiring managers and freelance clients. Use when asked to make a repository portfolio-ready, audit why it is not landing, rewrite the README or add a reviewer path, build an evidence spine or live demo, or answer "is this ready as a portfolio piece?".
license: MIT
metadata:
  version: "1.0.0"
---

# Portfolio Builder

A portfolio piece has one job: let a busy evaluator decide, in the time they actually give you, that
you can do the work. Features, architecture and documentation are evidence for that decision —
nothing more.

The default failure mode is a repository that is *good* but unreadable: no live demo, an essay of a
README, claims without artifacts, red checks, and a reviewer who leaves after ninety seconds. Fix the
evaluation path before adding another feature.

## Portability

This skill uses the standard Agent Skills format only. It requires no host-specific features, tools or
slash commands: any Agent-Skills implementation can load it, and the bundled audit script is Python
standard library, cross-platform and read-only. Host-specific verification commands appear only as
optional examples.

## Three readers, three budgets

| Reader | Budget | They look at | What loses them |
| --- | --- | --- | --- |
| Recruiter / sourcer | 30–60 s | Repo card (description, topics), README first screen, CI badge, one screenshot | Empty description, no live link, red checks, wall of text |
| Hiring manager / engineer | 5–15 min | Live demo or clone, one deep artifact, tests, ADRs, commit history | Claims with no artifact, stale docs, "production-ready" hand-waving |
| Freelance client | 2–5 min | The outcome in business terms, scope, proof you shipped something real | Engineering-first framing with no "what this bought" |

Pick one primary reader and one secondary. Do not average all three into a document that serves none.

## Non-negotiables

1. **Evidence over adjectives.** Every claim maps to a committed artifact: benchmark JSON/Markdown,
   a test, a CI run, an ADR, a verification record, a replay trace, media.
2. **Evaluable without cloning.** A live demo, static replay or 30–60 s video above the fold. Asking a
   recruiter to install anything is asking them to leave.
3. **Green checks.** Red CI on the default branch is a blocker. Fix the causes; never disable a gate to
   make a badge green.
4. **Honest limits.** A real-vs-simulated table and an explicit "not built" list. Reviewers trust the
   claims you *don't* make.
5. **One-command run, no optional infrastructure.** Clone → install → run. Docker, a database or a
   cloud account may be supported, never required for the demo.
6. **A fast first screen.** What it is, why it exists, what it proves, how to see it, how to review it.
7. **A complete repo card.** Description, topics, homepage/live URL, license.

## Workflow

### 0. Inventory (read-only)

Read before writing. Run the project if it runs.

```bash
git status && git log --oneline -10
head -80 README.md
ls tests docs .github/workflows 2>/dev/null
python -m pytest -q 2>/dev/null || npm test -- --run 2>/dev/null   # adapt to the stack
gh run list --branch main --limit 5          # if gh is authenticated
gh repo view --json description,repositoryTopics,homepageUrl,licenseInfo
```

Record: the one-sentence thesis, the strongest artifact, the weakest link, the primary audience.

### 1. Pin the thesis

Write one sentence: "<project> is a <thing> that <does X>, built to demonstrate <capability>."
If the sentence needs three clauses, the audience is unclear or the project is two projects.

### 2. Build the evidence spine

Measure → commit the artifact → cite it from the narrative. Never the reverse.

- Prefer **stable work metrics** (nodes expanded, operations, cache hits) over wall-clock, which is
  machine-noisy. Report both, and record the machine.
- State the **denominator** (200 sampled pairs, seven stops, 105k nodes) and the **baseline**.
- Prefer a **break-even or trade-off** over a single best number ("12 queries against A\*").
- Any preprocessing cost is reported separately from query cost.
- Regenerate artifacts in the same change that alters behavior. Never hand-edit generated output.
- Differential tests against a simple oracle turn "it works" into "it agrees with the reference".

See `references/evidence-spine.md` for artifact shapes and worked numbers.

### 3. Write the surface layer, in this order

1. **Repo card** — description, topics, homepage, social preview (`assets/repo-card.md`).
2. **README first screen** — pitch, at-a-glance table, one visual (`assets/readme-skeleton.md`).
3. **Reviewer page** — five-minute path, how it is built, real vs simulated, claims → evidence, role
   paths, not-built list (`assets/reviewer-page-template.md`).
4. **Origin** — why it exists; keep chronology honest and do not retrofit motives.
5. **Limits** — what is simulated, what is deliberately out of scope.
6. **Run** — three commands, default path free of optional infrastructure.

Rules: one screen, one idea; no adjective without a number; every claim links to its artifact.

### 4. Make it evaluable without cloning

Choose the cheapest artifact that shows the thing working:

| Option | When | Notes |
| --- | --- | --- |
| Hosted demo | Product-shaped project | Free-tier, seeded, rate-limited; URL in the repo card |
| Static replay | Algorithm/visual project | One self-contained HTML file, no network; publish on Pages |
| Screen recording | UI or workflow | 30–60 s, muted, committed or linked; poster frame inline |
| Screenshots | Any | Regenerate when the UI changes; keep them small |

Media budgets: GIF under ~1 MB, video under ~5 MB, screenshots under ~300 KB each. Anything larger
belongs behind a link, not in a clone.

### 5. Harden the repository

- One-command install and run; pinned versions; no `sudo`.
- CI matrix on the platforms you claim (the matrix itself is evidence).
- Gates that fail loudly: tests, lint, types, generated-artifact freshness.
- License, security notes, no secrets, no private data, no real customer records.
- Optional infrastructure is opt-in and documented with a clear failure message.

### 6. Truth pass

- List every number in the README; find its artifact. Any number without an artifact is either
  measured now or removed.
- Search for stale promises ("planned", "coming soon", "production-ready", "not implemented").
- Regenerate benchmarks, screenshots, replay traces and static pages; check they are committed.
- Compare docs against code: endpoints, commands, counts, file paths.
- Verify the real-vs-simulated table is still true.

### 7. Launch

Repo description, topics, homepage, social preview, enable Pages/hosting, pin the repository to the
profile. Then open the repo in a private window and take the 60-second test yourself.

See `references/launch-checklist.md`.

### 8. Maintain

- Generated artifacts and their gates ship together, so drift fails CI instead of reaching a reviewer.
- When behavior changes, numbers and media change in the same commit.
- Date every external-data snapshot and say how to regenerate it.
- Re-run the audit after any feature work that touches the demo, benchmarks or README.

## Audit mode

Run the mechanical checks, then the qualitative ones:

```bash
python .agents/skills/portfolio-builder/scripts/portfolio_audit.py . --remote --network --claims
```

`--remote` reads the repo card and the latest default-branch CI run (needs authenticated `gh`);
`--network` probes the hosted demo URL and fails on 4xx/5xx; `--claims` lists every numeric claim in
the README with its line and links, because the script cannot tell whether a number is still current.
The claim inventory is the bridge to the manual procedure in `references/audit-rubric.md`.

Then apply the 60-second test, the 10-minute test, and the severity table. Blockers to fix before
anything else: red or unknown CI, no live/replayable demo, a demo URL that does not resolve, empty
repo card, and claims contradicted by the committed artifacts.

## Writing rules

- **Numbers**: median + denominator + machine; baseline and trade-off; no precision theatre.
- **Voice**: active, concrete, short sentences. "The city query expands 85 nodes where Dijkstra needs
  53,885" beats "highly performant"; wall time is a parenthetical from a named run, not the headline.
- **Claims**: each one names its evidence. "All exact solvers agree with the Dijkstra oracle
  (`tests/routing/`)".
- **Honesty**: simulated is simulated; synthetic data is labelled; limitations are listed, not buried.
- **Origin**: why the project exists, in chronological order. Do not invent a motivation that only
  appeared later (an employer, a trend, a competition).

## Anti-patterns

- Tutorial clone with no original decision or measurement.
- README that explains the stack before saying what the thing does.
- "Production-ready" without backups, auth, monitoring or a load test.
- Metrics without a denominator, a baseline or a machine.
- Screenshots that no longer match the UI; benchmark numbers from an older commit.
- A demo that requires Docker/WSL/Postgres to open.
- Red checks with a note that "tests pass locally".
- Hiding the limitations; reviewers find them anyway and discount everything else.
- Fabricated users, logos or testimonials. Never.

## Guardrails

- Never invent metrics, users, employers, clients or testimonials.
- Do not claim production readiness; state the boundary of every guarantee.
- Do not deploy, enable Pages, or change public repository settings without explicit consent.
- Keep AI-assistance policy consistent with what the history shows; do not fabricate authorship.
- No secrets, private keys, customer data or private addresses in the repository or media.

## Worked example: Entrega Clara

This repository is the worked example — including its failures. The audit found: **red CI on main**,
an empty repository description with no topics, no hosted demo, and docs that still described
deferred work as future. The fixes were mundane and high-leverage:

- four real CI defects (a whitespace gate, runner-label drift, a Python 3.11 collection bug, a type
  check missing an optional dependency), fixed rather than skipped;
- a first-screen at-a-glance table and a [reviewer page](../../../docs/for-reviewers.md) with a
  five-minute path, real-vs-simulated and claims → evidence;
- an [origin document](../../../docs/origin.md) that separates the academic start from the portfolio
  layer and the later employer alignment;
- one committed benchmark artifact per claim, regenerated by the harness, gated by
  `scripts/check.py`.

The transferable pattern: audit the evaluation path, fix what blocks a reader, and let the engineering
speak through artifacts.

## Files

- `references/evidence-spine.md` — how to measure, record and cite evidence.
- `references/readme-and-reviewer-page.md` — surface patterns and prose rules.
- `references/audit-rubric.md` — 60-second and 10-minute tests, severity table, audit procedure.
- `references/launch-checklist.md` — repo card, hosting, media, pre-flight.
- `assets/readme-skeleton.md` — README skeleton to fill in.
- `assets/reviewer-page-template.md` — five-minute reviewer page template.
- `assets/repo-card.md` — description formula, topic sets, homepage rules.
- `scripts/portfolio_audit.py` — stdlib mechanical audit (links, license, CI, tests, metadata).
