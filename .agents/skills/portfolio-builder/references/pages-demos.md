# Pages demos and showcase pages

The repository is the proof. The demo is the front door. A recruiter decides in the first minute
whether the thing is worth the next ten, and a good demo lets them see the concept without cloning,
installing or creating an account.

This is a **showcase** artifact, not a second product. It is allowed to be a simulation, a replay or a
guided concept, as long as it is labeled, deterministic and tied to real artifacts from the repository.

## The demo contract

A piece demo has to do six things:

1. **Name the project and the claim.** The first screen says what it is and what the visitor will see.
2. **Show the artifact.** A route, a benchmark, a queue, a trace, a terminal result, a rendered document,
   a map, a chart, a workflow. Not a hero image with a paragraph.
3. **Offer one action.** Step, run, filter, drag, replay, compare. One obvious control is enough; a wall
   of fake controls is not.
4. **Be honest.** A concept demo says "static concept demo"; simulation, sample data and omitted
   features are visible. The real repository is linked.
5. **Return the visitor.** A link back to the repo, the portfolio/profile, the reviewer page, and the
   real app if it is hosted elsewhere.
6. **Be machine-checkable.** The source repository link, portfolio link, provenance marker, static or
   concept label, artifact and no remote API call are all visible in the HTML.

It must be static: no login, no API, no database, no Docker, no install, no build step at view time. It
must work on a phone and with a keyboard. It must be regenerable from committed inputs.

Every public, recruiter-facing piece gets a demo. The factory is the default: a backend, CLI, library,
data or full-stack project gets a concept demo, not a pass because Pages cannot run it. The contract is
standard; the artifact and composition are not.

## Choose a lane

| Lane | Best for | What Pages serves | What the visitor does |
| --- | --- | --- | --- |
| Static replay | Algorithms, simulations, data, visual systems | One self-contained page and committed JSON/traces | Step through a real run, compare results, inspect the evidence |
| Client-only app | Frontend products with deterministic seed data | A built static app, no server | Use the product flow against local fixtures |
| Concept demo | Backend, CLI, library, data/ML, full-stack, infrastructure | A static page that demonstrates the concept using recorded real input/output | Follow the scenario, inspect the actual output, open the repo for the implementation |
| Hosted product + concept demo | A full-stack product with a deployable frontend/API | The concept demo always; the real app only if it is hosted elsewhere | Try the real app, then use the concept demo when the backend is unavailable |
| Recording | Motion-heavy or destructive workflows where interaction is not feasible | A committed 30–60 s video with a poster | Watch the real behavior, then open the repo |

Prefer the interactive lane. A recording is a fallback, not the default. A screenshot is a supplement,
never the demo.

## The factory is a contract, not a template

The factory standardizes the contract and the return path, not the visual composition. A map wants a
map and a route control; a queue wants a timeline; a CLI wants a transcript with a command; a data
project wants a chart and a table; a product flow wants states and a next action. The masthead,
artifact, proof, limits and next sections are content commitments. They are not a fixed layout.

The skeleton is a starting contract. Replace the stage with the domain artifact and let the artifact
decide width, controls, density and emphasis. Do not ship the same shell with a swapped paragraph
across unrelated pieces; a recruiter should recognize the project before the template. The factory can
share the contract, the workflow and the access rules, but not one visual answer.

## Concept demos for projects that cannot run on Pages

GitHub Pages is static file hosting. It cannot run FastAPI, a database, a worker, a CLI or a native
binary. That is not a reason to ship no demo. Build a concept demo **beside the repository**:

- It uses committed, real sample data and real output from the project, not invented values.
- It is clearly labeled a static concept demo.
- It links to the actual repository, the portfolio/profile, and the real app when one is hosted.
- It shows the concept, not a fake version of the product. The implementation remains the proof.

### Backend / API

Show a real request and response, a state machine, a queue, a timeline or a short trace. Let the
visitor choose a scenario and see the same output the API returns. Include the endpoint/command and a
link to the handler or test that produced it. Do not invent latency, success rates or error counts.

### CLI / library

Show one real command and its output. A stepper that reveals the pipeline stage by stage is better than
a fake terminal. Show the transform, the input file and the final artifact. Link the command, the test
and the source file. A "copy command" block is useful; a typing animation is not evidence.

### Data / ML

Show a committed dataset slice, the pipeline, the output and one measured result. A small client-side
model is acceptable only if it uses the real trained artifact and is labeled; otherwise precompute the
outputs and replay them. State the sample size, the split and the metric. No invented accuracy.

### Full-stack product

The Pages demo can show the product flow against seed data: a menu, a cart, an order state machine, a
courier timeline. The real backend can be hosted elsewhere and linked; the Pages page is the concept
demo for the 60-second test and for when the backend is cold or unavailable. Never let a missing
backend lead to a fake success path.

### Infrastructure / systems

Show the topology, the failure scenario and the observed result as an interactive diagram or timeline.
Use a real run from the repository. Link the test or the verification record. Do not claim production
behavior.

## The page shape

A useful showcase page has one dominant artifact, not a grid of features.

1. **Masthead:** project name, one sentence, "Static concept demo" or "Live demo", and the repo link.
2. **The artifact:** one stage with one control. Let the visitor change one input and see the result.
3. **What just happened:** the concrete output, with units and provenance.
4. **What is real / simulated:** a short table. Name the sample, the dataset and the omitted pieces.
5. **How it maps:** input → process → output, with links to the real source, test or artifact.
6. **What to review next:** the repository, the portfolio/profile, the reviewer page, the real app if
   hosted.

Do not re-create the README. Do not add a feature-card grid, a fake dashboard, a fake user count or a
"book a call" conversion block.

## Build recipes

### Vanilla static replay

- Keep one `site/index.html`, inline CSS and JS, and a committed JSON/trace beside it.
- Load the data with `fetch("./data.json")`, or inline it for a single-file page.
- No CDN, no font download, no analytics. The page must work from `file://` or a static server.
- Use relative URLs so the project Pages base path works without configuration.
- Start with `assets/pages-demo-skeleton.html` and fill the artifact slot.
- Verify with `python -m http.server 4173 -d site` and open the page.

### Vite / React / client-only app

- Set the Vite `base` to `/<repo>/` for project Pages.
- Build to `dist/`; upload `dist/` with the workflow template.
- Keep all data in committed fixtures. No `fetch` to an API, no runtime secrets.
- Hash routing is the simplest Pages-safe router; if you use history routing, ship a `404.html` copy
  of `index.html` and verify deep links.
- A client-only app is a concept demo if it uses fixtures, not the real backend. Label it.

### Next.js static export

- Set `output: "export"` and `images: { unoptimized: true }`.
- Set `basePath` and `assetPrefix` to `/<repo>` for project Pages.
- Remove or replace server routes, API routes, middleware and dynamic server rendering.
- Use client-side fixtures for data. If the app depends on a backend, ship the concept demo instead.
- Export to `out/`; upload `out/` with the workflow template.
- Verify the exported HTML works from a plain static server, not only `next dev`.

### Python / backend

- Pages cannot run Python. Export a deterministic scenario from the real code: JSON, a trace, a set of
  outputs and the command that produced them.
- Build the static page around that export; link the backend source, the test and the live API if one
  is hosted.
- Keep the export script in the repository and regenerate the artifact in the same change as behavior.

### Recorded fallback

- 30–60 seconds, muted, with a poster frame and a caption.
- Show a real interaction; do not stage a fake success state.
- Keep it under ~5 MB or link it instead of committing it.
- Pair it with the concept demo, not instead of the repository.

## Pages mechanics

- **Project URL:** `https://<owner>.github.io/<repo>/`. The base path is `/<repo>/`; relative URLs or a
  configured base path are mandatory.
- **Workflow:** copy `assets/pages-demo-workflow.yml` to `.github/workflows/pages.yml`, adapt the
  artifact path, and commit it.
- **Enable Pages once:** `gh api --method POST repos/<owner>/<repo>/pages -f build_type=workflow`
  (use `PUT` if it already exists). This is a public setting: ask first.
- **Permissions:** `pages: write` and `id-token: write`; use the `github-pages` environment.
- **Deployment is an operator action:** do not enable Pages or deploy without explicit consent.
- **Custom domain:** optional; the base path changes. Test the final URL, not only the build output.
- **Cache:** the deployed page should be a few hundred KB; avoid giant data files in the critical path.

## Verify the showcase

1. Build the page from a clean tree; regenerate the committed data.
2. Serve it locally with a static server, not the app dev server.
3. Open it in a private window at 1440 and 390. The first screen names the project and shows the artifact.
4. Use the primary control with the keyboard only. Every action has a visible result and a reset.
5. Check the console: no errors, no requests to an API, no missing assets. The page works offline.
6. Check the page title and a text marker. A 200 response with an empty shell is not a demo.
7. Run the portfolio audit with `--network --demo-contract`; it verifies the page title, the project
   name, the repository link, the portfolio link, provenance, the label, an artifact and no direct
   remote API call.
8. Visit the deployed Pages URL from the README and the repo card.

## Audit the contract

```bash
python .agents/skills/portfolio-builder/scripts/portfolio_audit.py . \
  --remote --network --demo-contract \
  --portfolio-url https://github.com/<owner>
```

The contract is a floor, not a design review. It fails when the source repository link is missing. It
warns on a missing portfolio/profile link, provenance marker, static/concept label, interactive or
visual artifact, or a direct remote API call. A warning is visible work, not a pass; fix it or state why
the page is an exception. The manual 60-second test still decides whether the artifact is convincing.

## Portfolio consistency

- Every public piece gets a demo link in the README first screen and the repo card homepage.
- Use the same demo URL shape (`/<repo>/`) and the same navigation contract: repository link, portfolio
  link, what is simulated, reviewer path.
- Every demo returns to the portfolio/profile, not only to its own repository. Use the dedicated
  portfolio site when one exists; otherwise use the owner's GitHub profile. This is the path a recruiter
  follows from one piece to the next.
- A separate `-demo` repository is acceptable when the actual repository cannot include the site; link
  both ways and keep the actual repository as the primary piece.
- A portfolio index that lists the demos is a hub, not a piece. It is out of scope for this skill; the
  per-repo demos link back to it, but the hub is not audited or scored here. Keep the per-repo demo and
  repo card correct first.

## Anti-patterns

- A 200 response with no title, no artifact and no working control.
- A static screenshot labeled "demo".
- A fake dashboard with invented users, metrics, latency or success rates.
- A concept demo that pretends to be the deployed product.
- A Pages deploy of a Next.js app that still has server routes or API calls.
- A demo that requires an API, a database, a login or Docker to open.
- A generic landing page with three feature cards and no domain artifact.
- A recording with a staged success state that the repository cannot reproduce.
- No link back to the repository or the portfolio/profile, or no statement of what is simulated.
- The same shell with a swapped artifact across unrelated pieces; the factory contract is shared, the
  composition is not.
- A direct remote API call in a page that claims to be a static demo.
