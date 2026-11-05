---
name: portfolio-builder
description: Tailor public, recruiter-facing repositories into credible portfolio pieces for recruiters, hiring managers and freelance clients. Use when asked to make a public repository portfolio-ready, audit why it is not landing, rewrite the README or add a reviewer path, build an evidence spine or GitHub Pages showcase demo, or answer "is this ready as a portfolio piece?". Includes a labeled static concept demo for projects that cannot run on Pages, a portfolio return path, and a machine-checkable demo contract. Private repositories and hub/collection repositories are out of scope; the audit reports SKIP and stops.
license: MIT
metadata:
  version: "1.7.0"
---

# Portfolio Builder

A portfolio piece has one job: let a busy evaluator decide, in the time they actually give you, that
you can do the work. Features, architecture and documentation are evidence for that decision —
nothing more.

A portfolio piece has two surfaces: the repository proves the work; the showcase demo lets a busy
visitor see the concept before they read the code. Build both.

The default failure mode is a repository that is *good* but unreadable: no live demo, an essay of a
README, claims without artifacts, red checks, and a reviewer who leaves after ninety seconds. Fix the
evaluation path before adding another feature.

**Scope:** public, recruiter-facing piece repositories. Private repositories and hub/collection
repositories are out of scope: the audit reports `SKIP` and stops. Copy the skill into the individual
public piece repository instead.

## Portability

This skill uses the standard Agent Skills format only. It requires no host-specific features, tools or
slash commands: any Agent-Skills implementation can load it, and the bundled audit script is Python
standard library, cross-platform and read-only. The local audit is host-agnostic; `--remote` assumes
GitHub (`gh`, Pages, repository metadata), and `--network` only needs HTTP. Host-specific verification
commands appear only as optional examples.

## Three readers, three budgets

| Reader | Budget | They look at | What loses them |
| --- | --- | --- | --- |
| Recruiter / sourcer | 30–60 s | Repo card (description, topics), README first screen, CI badge, one screenshot | Empty description, no live link, red checks, wall of text |
| Hiring manager / engineer | 5–15 min | Live demo or clone, one deep artifact, tests, ADRs, commit history | Claims with no artifact, stale docs, "production-ready" hand-waving |
| Freelance client | 2–5 min | The outcome in business terms, scope, proof you shipped something real | Engineering-first framing with no "what this bought" |

Pick one primary reader and one secondary. Do not average all three into a document that serves none.

## The showcase surface

The demo is the 30-second surface; the repository is the 10-minute surface. A good showcase names the
project, shows one real artifact and offers one action, without a login, an API, a database or an
install. GitHub Pages is the default home because it is static, public and free.

When the real project cannot run on Pages because it is a backend, CLI, library, data pipeline or
full-stack app, build a **static concept demo** beside it: committed sample input/output, the real
artifact, a clear "this is a simulation" statement and a link to the implementation. The demo is a
front door, not a fake product. Every public piece gets this demo; the factory is the default, not an
exception for projects without a frontend.

The factory standardizes the contract, not the composition. The map, queue, transcript, chart or trace
determines the stage, controls and density; do not ship the same shell with a swapped artifact across
unrelated pieces. Every demo returns to the source repository and to the portfolio/profile, because the
portfolio index is a hub and this skill does not audit it.

See `references/pages-demos.md` for the lanes, the contract, the page recipes and the acceptance
checks.

## Non-negotiables

1. **Evidence over adjectives.** Every claim maps to a committed artifact: benchmark JSON/Markdown,
   a test, a CI run, an ADR, a verification record, a replay trace, media.
2. **Evaluable without cloning.** A live demo, static replay, concept demo or 30–60 s video above the
   fold. A project that cannot run on Pages still gets a labeled static concept demo beside the
   repository, with links back to the source and the portfolio. Asking a recruiter to install anything
   is asking them to leave.
3. **Green checks.** Red CI on the default branch is a blocker. Fix the causes; never disable a gate to
   make a badge green.
4. **Honest limits.** A real-vs-simulated table and an explicit "not built" list. Reviewers trust the
   claims you *don't* make.
5. **One-command run, no optional infrastructure.** Clone → install → run. Docker, a database or a
   cloud account may be supported, never required for the demo.
6. **A fast first screen.** What it is, why it exists, what it proves, how to see it, how to review it.
7. **A complete repo card.** Description, topics, homepage/live URL, license.

## Scope

Only public, recruiter-facing piece repositories. The audit returns `SKIP` and stops when:

- the repository is private (`--remote` checks with `gh`), or
- it is a hub/collection: a README that identifies a hub/collection, or at least two subprojects with
  no root application code.

Without `--remote`, privacy cannot be checked; the audit warns instead of assuming the repository is
public.

Copy the skill into an individual public piece repository. Private working repositories and
collections are not portfolio pieces; missing demos, licenses or social cards are not defects there.

## Workflow

### 0. Inventory (read-only)

Read before writing. Run the project if it runs. If the audit returns `SKIP`, stop: the repository is
private or a hub, not a public piece.

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

Every public piece gets a demo. Choose the lane that shows the thing working:

| Option | When | Notes |
| --- | --- | --- |
| Hosted demo | Product-shaped project with a deployable frontend/API | Free-tier, seeded, rate-limited; URL in the repo card |
| Static replay | Algorithm/visual/data project | One self-contained HTML file, no network; publish on Pages |
| Concept demo | Backend, CLI, library, data/ML, infrastructure or full-stack | A static page using committed sample input/output; label the simulation and link the real repo |
| Screen recording | Motion-heavy or destructive workflow | 30–60 s, muted, committed or linked; poster frame inline |
| Screenshots | Any | Regenerate when the UI changes; a supplement, never the whole demo |

Media budgets: GIF under ~1 MB, video under ~5 MB, screenshots under ~300 KB each. Anything larger
belongs behind a link, not in a clone.

The factory contract is fixed: source repository link, portfolio/profile return link, provenance
marker, static/concept label, at least one interactive or visual artifact, and no direct remote API
call. The artifact determines the composition. The skeleton is a starting contract, not a layout to
copy across pieces. Run the contract check with `--network --demo-contract`; see
`references/pages-demos.md` for the commands and the exceptions.

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
profile. The homepage is the demo; for a project that cannot run on Pages, it is the concept demo.
The demo links back to the source repository and the portfolio/profile. Then open the repo in a private
window and take the 60-second test yourself.

See `references/launch-checklist.md`.

### 8. Maintain

- Generated artifacts and their gates ship together, so drift fails CI instead of reaching a reviewer.
- When behavior changes, numbers and media change in the same commit.
- Date every external-data snapshot and say how to regenerate it.
- Re-run the audit after any feature work that touches the demo, benchmarks or README.

## Audit mode

Run the mechanical checks, then the qualitative ones:

```bash
python .agents/skills/portfolio-builder/scripts/portfolio_audit.py . \
  --remote --network --demo-contract --claims
```

`--remote` reads the repo card, the latest default-branch CI run, repository privacy, whether the
custom social preview is actually set, and whether the profile pins or names the repository (needs
authenticated `gh`);
`--network` probes every external link in the documentation, then the hosted demo URL, and fails on
404/410; `--demo-contract` checks the page for the
source repository link, portfolio/profile link, provenance, label, artifact and no direct remote API
call. Pass `--portfolio-url <url>` when the portfolio has a dedicated address; otherwise the owner's
profile link is accepted. `--claims` lists claim-like numeric lines with their section and any links,
because the script cannot tell whether a number is still current. The claim inventory is the bridge to
the manual procedure in `references/audit-rubric.md`.

A `SKIP` result means the repository is private or a hub: stop, do not apply the piece tests, and move
to the individual public piece repository. For CI, add `--fail-on-skip` so an out-of-scope repository
does not pass silently.

Then apply the 60-second test, the 10-minute test, and the severity table. Blockers to fix before
anything else: red or unknown CI, no live/replayable demo, a demo URL that does not resolve, a demo
with no source-repository return path, an empty repo card, and claims contradicted by the committed
artifacts.

## Writing rules

- **Numbers**: median + denominator + machine; baseline and trade-off; no precision theatre. When
  each row of a table is an independently drawn sample, say so beside the table — the comparison is
  within a row, never across rows.
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
- A Pages demo that still needs a backend, a login or an install.
- A concept demo that invents metrics or pretends to be the deployed product.
- A 200 response with no title, artifact or working control.
- A demo with no way back to the source repository or the portfolio/profile.
- A one-way loop: the demo links to the profile, and the profile neither pins nor names the project.
- A benchmark table whose rows draw independent samples, with nothing saying so; the 13-stop row
  comes out cheaper than the 11-stop one and reads as a bug.
- The same shell with a swapped artifact across unrelated pieces.
- A direct remote API call in a page that claims to be static.
- A screenshot labeled "demo".
- Red checks with a note that "tests pass locally".
- Hiding the limitations; reviewers find them anyway and discount everything else.
- Fabricated users, logos, testimonials or metrics. Never.

## Guardrails

- Never invent metrics, users, employers, clients or testimonials.
- Do not claim production readiness; state the boundary of every guarantee.
- Do not deploy, enable Pages, or change public repository settings without explicit consent.
- GitHub Pages is static hosting. A backend cannot run there; ship a concept demo instead.
- Label every concept demo, link the real repository, and never invent values to fill the page.
- Every demo returns to the portfolio/profile as well as the repository. The portfolio index is a hub;
  do not audit it here, but do link to it.
- Keep AI-assistance policy consistent with what the history shows; do not fabricate authorship.
- No secrets, private keys, customer data or private addresses in the repository or media.

## Worked example: Entrega Clara

The source repository (Entrega Clara) is the worked example — including its failures. The audit found: **red CI on main**,
an empty repository description with no topics, no hosted demo, and docs that still described
deferred work as future. The fixes were mundane and high-leverage:

- four real CI defects (a whitespace gate, runner-label drift, a Python 3.11 collection bug, a type
  check missing an optional dependency), fixed rather than skipped;
- a first-screen at-a-glance table and a `docs/for-reviewers.md` page with a five-minute path,
  real-vs-simulated and claims → evidence;
- a `docs/origin.md` that separates the academic start from the portfolio layer and the later
  employer alignment;
- one committed benchmark artifact per claim, regenerated by the harness, gated by
  `scripts/check.py`;
- a static lab that demonstrates the route comparison in the browser and is hosted on Pages, while the
  full FastAPI/Next app stays a local demo linked from the same first screen; the lab links back to the
  repository and the owner's profile.

The transferable pattern: audit the evaluation path, build the demo as the front door, return the
visitor to the portfolio, and let the repository prove the engineering through artifacts.

## Files

- `references/evidence-spine.md` — how to measure, record and cite evidence.
- `references/readme-and-reviewer-page.md` — surface patterns and prose rules.
- `references/audit-rubric.md` — 60-second and 10-minute tests, severity table, audit procedure.
- `references/pages-demos.md` — demo lanes, concept demos, Pages recipes and acceptance checks.
- `references/launch-checklist.md` — repo card, hosting, media, pre-flight.
- `assets/readme-skeleton.md` — README skeleton to fill in.
- `assets/reviewer-page-template.md` — five-minute reviewer page template.
- `assets/repo-card.md` — description formula, topic sets, homepage rules.
- `assets/pages-demo-skeleton.html` — accessible static concept-demo starting page.
- `assets/pages-demo-workflow.yml` — GitHub Pages deployment workflow to adapt.
- `scripts/portfolio_audit.py` — stdlib mechanical audit (repo-wide links including external URLs,
  license, CI, tests, metadata, profile return path, demo page and demo contract).
