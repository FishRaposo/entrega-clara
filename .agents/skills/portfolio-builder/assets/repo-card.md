# Repo card

The repo card is what a recruiter sees before opening anything: name, description, topics, homepage,
language bar, last commit. Treat it as the title slide.

## Description formula

`<What it is>: <domain or technique>. <One proof point or capability>.`

Examples:

- "Pathfinding on real São Paulo streets, framed as a food-delivery platform. City-scale graph, measured solver ladder, live lab."
- "Capacitated vehicle routing with promised windows. Exact and heuristic solvers, differential tests, committed benchmarks."
- "A tiny HTTP framework for embedded devices: 8 KB binary, zero dependencies, deterministic tests."

Rules:

- One sentence, under ~160 characters.
- Never start with "A" or "This is"; start with the noun.
- No emoji, no hype words, no "portfolio project".
- Include one concrete proof point when it fits (size, scale, latency).

## Topic sets

Pick 6–10; they are search terms, not decoration.

| Project shape | Suggestions |
| --- | --- |
| Product / full-stack | domain (`food-delivery`, `logistics`), stack (`fastapi`, `nextjs`, `typescript`, `python`), data (`openstreetmap`), practice (`postgresql`, `docker`) |
| Algorithms / systems | technique (`pathfinding`, `dijkstra`, `astar`, `contraction-hierarchies`, `vehicle-routing`), language, benchmark (`benchmark`) |
| Library / tool | language, ecosystem, use case, `cli`, `developer-tools` |
| Data / ML | domain, method, tooling, `visualization`, `reproducible-research` |

Lowercase, hyphenated, no vanity tags.

## Homepage

- Point to the live demo or static concept demo first; docs second. Never leave it empty when a demo
  exists.
- For a backend, CLI, library or full-stack piece that cannot run on Pages, the homepage is the concept
  demo; the page must say it is a simulation and link the real implementation.
- Every demo links back to the portfolio/profile. The profile README is the shared hub; the per-repo
  card does not replace it.
- If the demo needs a login, link a public read-only view instead.

## Social preview

- 1280×640 PNG/JPG.
- Project name, one sentence, one number.
- Same palette as the README hero; no text smaller than ~24 px.

## Profile integration

- Pin the repository.
- One line in the profile README with the link and the proof point.
- Keep the pinned set small: three to six repos, each with a description.
