# README and reviewer page

Two surfaces do most of the portfolio work: the README (the 60-second answer) and a reviewer page (the
five-minute pass). Both are structured, not written as essays.

## README architecture

Order matters. A reader who stops after one screen should still know what the project is, why it
exists, what it proves, and how to see it.

1. **Title and one-line thesis.** What it is, whose problem it solves, one proof point. No stack list.
2. **Hero visual.** A screenshot, GIF or demo/concept-demo link that shows the thing working.
3. **At-a-glance table.** What it is · what it proves (one or two numbers) · engineering counts ·
   see-it-without-running · how to review. Five rows, scannable.
4. **Measured evidence.** The shortest table that carries the thesis, with a link to the full artifact.
5. **Audience section** (optional but valuable when there is a specific reader, e.g. a sector or a
   role). State the chronology honestly; never claim the project was built for that reader.
6. **Origin.** Why it exists, in order. One screen.
7. **Built vs deferred.** Two columns. The deferred column is a feature, not a confession — it shows
   judgment.
8. **See it without running it.** Live demo, static replay, concept demo, video, screenshots, and a
   portfolio/profile link. A concept demo is labeled as a simulation and links the real implementation.
9. **Run it.** Three commands, default path free of optional infrastructure.
10. **Limits and attribution.** Simulated vs real, license, data attribution.

Keep the first screen under ~40 lines. Long READMEs are fine after that; readers self-select.

### Example: the at-a-glance table

```markdown
## At a glance

| | |
| --- | --- |
| **What it is** | A São Paulo food-delivery platform where the courier drives the computed route. |
| **What it proves** | CH answers in 85 expansions (0.1% of the graph) where Dijkstra needs 53,885 (51.3%); 2.8 ms vs 172 ms on the committed run. |
| **Engineering** | Python/FastAPI + Next.js; 291 backend tests, 3 browser journeys, 12 ADRs, 11 gates. |
| **See it now** | [Static lab](site/index.html) · [35-second tour](docs/media/demo-tour.webm) · [Portfolio](<profile URL>) |
| **Review it** | [Reviewer guide](docs/for-reviewers.md) — five-minute path, real vs simulated. |
```

### Example: built vs deferred

| Built | Deferred (documented, not required to run) |
| --- | --- |
| Time-dependent routing from a validated profile | Live traffic feeds |
| Capacitated batching with promised windows | Real payment providers |

## Reviewer page

A separate page (`docs/for-reviewers.md` or equivalent) that assumes a technical reader with five
minutes and no patience for marketing.

- **What this is** — three sentences, link the origin.
- **How it is built** — four to six bullets: architecture, where the domain lives, what is optional.
- **The five-minute path** — a table of minute → link → what it shows. End with the one number that
  matters.
- **Real vs simulated** — two columns, no hedging.
- **Claims → evidence** — three to five rows: claim, artifact, test. This is the section that converts
  skepticism into trust.
- **Pick a path** — recruiter, algorithms, backend, frontend; each with links and a time estimate.
- **Run it** — three commands.
- **Not built** — explicit list with boundaries.

## Client-facing path

If the primary reader is a freelance client rather than an employer, add a short block after the
measured evidence. Clients scan for a problem they recognize and a result they can buy:

- **Problem** — the business problem in the client's words, one or two sentences.
- **Scope** — what was delivered, what was explicitly excluded, and the constraint that shaped it.
- **Outcome** — the measured result or the capability that now exists; one number if possible.
- **Proof and handover** — the artifact, the run path, the documentation, and the maintenance terms.

Keep it to one screen and do not repeat the engineering ladder. A client who wants depth will follow
the reviewer page.

## Prose rules

- One screen, one idea. If a section has two theses, split it.
- Active voice, short sentences, concrete nouns.
- No adjective without a number: "fast" → "85 expansions (0.1% of the graph)"; "scalable" → "105k
  nodes". Wall time is a parenthetical from a named run.
- Every claim links to its artifact, in the same sentence or the next one.
- Say what is simulated next to the thing that is simulated, not in a footnote.
- Never imply production use: state the non-production boundary once, plainly.
- Bilingual reads: if the audience is local, a short section in their language beats a full
  translation; keep the technical tables in one language to avoid drift.

## Anti-patterns

- A README that starts with architecture or installation.
- A table with more than six columns.
- Screenshots without captions that explain what the reader is looking at.
- "Coming soon" sections that have been there for months.
- A reviewer page that repeats the README instead of giving a path.
- Claims that live only in the pitch and nowhere in the verification record.
- An engineering-first page with no outcome a client can recognize.
