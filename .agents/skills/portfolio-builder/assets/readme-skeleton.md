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
| **See it without running it** | [<demo/lab>](<url or path>) · [<video>](<path>) |
| **Review it** | [Reviewer guide](<path>) — five-minute path, real vs simulated. |

<One line: no Docker/database/account is required for the default run.>

## <The thesis section: measured evidence>

<The shortest table that carries the claim. Denominators, baseline, machine. Link the full artifact.>

## <Audience section — optional>

<If a specific reader matters, say what relevance means and state the chronology honestly.>

## Origin

<Why the project exists. Two short paragraphs. Chronological; no retrofitted motives.>

## Built vs. deferred

| Built | Deferred (documented, not required to run) |
| --- | --- |
| <capability + evidence> | <known gap + boundary> |

## See it without running it

- **<Static replay / demo>:** <path or URL>, <what it shows>.
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
- The demo link appears above the fold.
- The license and attribution are present.
