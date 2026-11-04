# README skeleton

Fill every placeholder. Delete sections that do not apply, but keep the order: the first screen must
answer what, why, proof, see, review.

```markdown
# <Project name>

**<One-line thesis: what it is, whose problem, one proof point.>** <Two or three sentences: what was
built, why it exists, the strongest measured claim. No stack list.>

![<caption that says what the reader is looking at>](<path to media>)

*<One sentence explaining the visual; if it was generated, name the generator and that it has no extra
dependencies.>*

## At a glance

| | |
| --- | --- |
| **What it is** | <domain framing in one sentence> |
| **What it proves** | <one or two measured numbers with a baseline> |
| **Engineering** | <stack>; <test counts>; <ADRs/gates> |
| **See it without running it** | [<demo, concept demo or lab>](<url or path>) · [<video>](<path>) · [Portfolio](<profile or portfolio URL>) |
| **Review it** | [Reviewer guide](<path>) — five-minute path, real vs simulated. |

<One line: no Docker/database/account is required for the default run.>

## <The thesis section: measured evidence>

<The shortest table that carries the claim. Denominators, baseline, machine. Link the full artifact.>

## <Audience section — optional>

<If a specific reader matters, say what relevance means and state the chronology honestly.>

## For freelance clients (optional)

**Problem:** <the business problem in the client's words>.
**Scope:** <what was delivered, what was explicitly excluded>.
**Outcome:** <measured result or the capability that now exists>.
**Handover:** <docs, tests, run path, maintenance>.

## Origin

<Why the project exists. Two short paragraphs. Chronological; no retrofitted motives.>

## Built vs. deferred

| Built | Deferred (documented, not required to run) |
| --- | --- |
| <capability + evidence> | <known gap + boundary> |

## See it without running it

- **<Static replay / live demo / concept demo>:** <path or URL>, <what it shows>. If it is a concept
  demo, say what is simulated and link the real implementation.
- **Portfolio:** <profile or portfolio URL>. The demo and this README should both return there.
- **<Recorded tour>:** <path>, <duration, size>.
- **Screenshots:** <path>.

## Run it

```bash
<install>
<run>
<verify>
```

<What the default mode does not require.>

## Limits and attribution

<Simulated vs real. Data licenses. Non-production boundary, once, plainly.>
```

## Checks before committing

- First screen under ~40 lines.
- Every number links to an artifact.
- Every relative link resolves.
- The demo or concept demo link appears above the fold and resolves.
- The demo links back to the repository and the portfolio/profile.
- A concept demo is labeled as such and links the real repository; it does not imply a live backend.
- The license and attribution are present.
- If clients are an audience, the problem → scope → outcome → handover block is present.
