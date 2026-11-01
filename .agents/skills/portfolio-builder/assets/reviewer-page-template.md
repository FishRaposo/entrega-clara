# Reviewer page template

Use for `docs/for-reviewers.md` (or the equivalent). One page, technical reader, five minutes.
Delete the examples and keep the structure.

```markdown
# Reviewing <project>

One page, roughly five minutes, for a recruiter, hiring manager or technical reviewer who wants to
judge the repository without reading all of it. Each step says what to look at and what it proves.

## What this is

<Three sentences: the thing, its domain, its origin. Link the full story. State plainly what it is
not (a clone, a startup pitch, a tutorial).>

## How it is built

- **<Architecture in one line.>** <Where the domain lives; where adapters live.>
- **<One command layer / one API / one entry point.>** <Why that matters for review.>
- **<What is optional.>** <Default path without infrastructure.>
- **<Observability and gates.>** <What the checks cover.>

## The five-minute path

| Minute | Open | What it shows |
| --- | --- | --- |
| 1 | <README evidence table> | <the headline measurement> |
| 2 | <demo / static replay> | <the thing working> |
| 3 | <full benchmark artifact> | <raw numbers, baseline, cost> |
| 4 | <verification record> | <gates, counts, scope notes> |
| 5 | <the key ADR> | <trade-off and rejected alternatives> |

If you only read one number: **<number with baseline and cost>.**

## What is real, what is simulated

| Real | Simulated or synthetic |
| --- | --- |
| <data / algorithms / tests / persistence> | <payments, identity, traffic, data> |

## Claims and where they are proven

| Claim | Evidence |
| --- | --- |
| <claim> | <artifact + test> |

## Pick a path

- **Recruiter / hiring manager (<n> min):** <links>.
- **<Domain> engineer (<n> min):** <links>.
- **Backend / platform (<n> min):** <links>.
- **Frontend (<n> min):** <links>.

## How to run it

```bash
<three commands>
```

<Default mode requirements; optional infrastructure and where it is documented.>

## What is deliberately not built

<Explicit list with boundaries; link the scope notes.>
```

## Checks before committing

- The five-minute table links to files that exist.
- The "one number" is in the benchmark artifact, not only here.
- Real vs simulated is still true after the last change.
- The not-built list matches the README's deferred column.
