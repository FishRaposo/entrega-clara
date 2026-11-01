# Origin

**Status:** Background — why this repository exists. Not a specification; the product contract lives
in [the M1 design](superpowers/specs/2026-09-01-milestone-1-core-delivery-loop-design.md) and the ADRs.
A Portuguese summary is at the end.

Entrega Clara was not born as a startup idea, an iFood clone, or a portfolio stunt. It was born from
noticing that two unrelated undergraduate assignments described two halves of the same system, and
deciding to build the system instead of submitting two separate exercises.

Everything else grew from that decision.

## 1. Two assignments, one system

One class required a requirements document for a food-delivery application: customers, restaurants,
menus, carts, checkout, couriers, delivery states, support. The other introduced brute-force route
optimization: try every possible ordering of stops and keep the cheapest.

Neither assignment asked for the other half. That was the creative leap: a delivery platform needs
routing, and a routing algorithm becomes far more interesting when it runs inside a real operational
workflow — real streets, real stops, real promises.

So the requirements document stopped being a document and became the product surface, and the
optimizer stopped being a demonstration and became the dispatcher.

## 2. The classroom algorithm became the starting point, not the destination

Brute force is a fine teaching tool and a terrible router: it is exact, and it dies at about ten
stops. The obvious move would have been to delete it once something better existed. Instead it stayed
in the repository as `LegacyBruteForceTSPSolver`, where it does three jobs:

- it is the **correctness oracle** for every exact replacement;
- it is the **baseline** in [the benchmark table](benchmarks/routing.md), so "better" is a measured
  claim rather than an adjective;
- it is the **company's first router** in the demo's fictional history — the system the company
  outgrew, kept in the code with a contract note explaining why it was replaced.

That last part is the joke that keeps paying off: a coursework algorithm about combinatorial
explosion became an in-world piece of legacy technical debt, complete with a documented migration
rationale. Learning about technical debt is one thing; shipping a company that could plausibly have
some is another.

## 3. More was built than either assignment required

The assignments implied a document and an algorithm. The repository has both, plus the system around
them: customers browsing menus, carts, idempotent checkout, simulated payments, the restaurant queue,
courier offers, batching, pickup and delivery states, GPS that follows the computed route, SSE
tracking, and an operations view with ETA accuracy.

That was a deliberate choice, not scope drift. The full loop is what turns algorithm questions into
engineering questions:

- What happens when a courier carries several orders at once?
- How do pickup-before-dropoff constraints change the route?
- What happens when a new order arrives while a delivery is active?
- How do time of day and promised windows change the answer?
- When is a faster algorithm worth its preprocessing cost?

Each of those started as a later extension, not as an assignment requirement.

## 4. It then became a portfolio project

Once the product worked, it had a second use: showing professional capability. The audience is
prospective employers and freelance clients, and the repository is built to be inspectable — measured
benchmarks, ADRs, verification counts, a lab anyone can open, committed screenshots, and a
self-contained replay of the committed traces.

One positioning detail matters. The author's professional background already includes substantial
applied-AI work. This project is deliberately the complement: a conventional software system with
domain modeling, transaction boundaries, state machines, algorithms, tests and trade-offs —
engineering that does not need a model in the loop to be interesting. AI is not bolted on, because the
point is to demonstrate the rest of the toolkit.

## 5. "Downscaling" meant infrastructure, not functionality

An earlier description of "downscaling the portfolio" was about operational friction, and it is worth
being precise: nothing was cut from the product, the algorithms, or the code quality. What was removed
was the requirement to install Docker Desktop and WSL just to run or demonstrate the project after a
Windows reinstall.

Docker is known and used professionally. It is simply not a prerequisite for a portfolio piece that a
recruiter might open between meetings. So the default path is Python and Node only, the database is
optional, and the demo runs offline. Depth stayed; ceremony left.

That choice also serves the portfolio: a reviewer can clone, run and inspect the application without
assembling an infrastructure department first.

## 6. iFood came afterwards

This chronology is easy to get backwards, so it is stated plainly: the project was **not** built for
iFood. It was built because two assignments fit together, then expanded into a working platform and a
portfolio piece. Only later did an application to iFood's Programa GenAI 2027 make the domain
alignment obvious — at which point the repository already contained a food-delivery platform.

The recruiter-facing section in the README was added at that point. The underlying project was
independently conceived, which is a stronger story than an imitation built to impress a specific
company.

## 7. What the later additions changed

Durable PostgreSQL persistence, a transactional outbox, process metrics, city-scale contraction
hierarchies, time-dependent routing, capacity and promised windows with dynamic re-insertion, and a
self-contained static demo all arrived after the initial product. They strengthen the portfolio
answer, and they are documented as engineering decisions with measured evidence.

They do not change the origin. The repository is still the answer to "what if the two assignments
were the same system?"

## 8. How it was built

Development is AI-assisted. The author uses Command Code as a pairing tool, and the commits say so:
they carry a `Co-authored-by: CommandCodeBot` trailer rather than hiding the assistance. The model
drafts code, tests and documentation; the author reviews and owns every change.

The gates are the contract: `scripts/check.py` runs the eleven checks (tests, lint, types, seed
validation, requirement coverage, app boundary, static-lab freshness and benchmark smoke), and the
measured artifacts are produced by the committed harness, not written by hand. Where a model-generated
change was wrong, the failure stays in the history and is fixed in a later commit. The numbers in this
repository are regenerated from code, not narrated.

## The causal chain

1. **Two assignments:** a food-delivery requirements document and a brute-force route-optimizer
   exercise.
2. **One application:** implement the delivery platform so routing has a real context.
3. **Engineering exploration:** keep brute force as the baseline, add better algorithms, measure them.
4. **Portfolio development:** demonstrate end-to-end software engineering beyond isolated algorithms
   or AI integrations.
5. **Accessibility and reproducibility:** remove unnecessary infrastructure requirements while
   preserving functionality.
6. **Career alignment:** the iFood application makes an independently built project especially
   relevant.

## What this is not

- Not an iFood clone; it was not built for or modelled on their product.
- Not a startup pitch; there is no commercial claim, and the non-production boundary is explicit.
- Not an algorithm exercise with a UI bolted on; the product surfaces drive the same command handlers
  the tests and the scenario runner use.
- Not an AI showcase; it is the conventional-engineering counterpart to that work.

## Resumo em português

O Entrega Clara nasceu de dois trabalhos de faculdade que descreviam metades do mesmo sistema: um
documento de requisitos de um app de delivery e um exercício de otimização de rotas por força bruta.
Em vez de entregar dois exercícios isolados, a decisão foi implementar o sistema que os dois juntos
implicavam.

A força bruta ficou no código como baseline e oráculo de corretude, e virou o roteador legado da
empresa fictícia — o sistema que ela superou, mantido com a justificativa documentada de por que foi
substituído. O restante do produto (cardápio, sacola, checkout, fila do restaurante, entregador,
lote, rastreamento, operações) existe para dar contexto operacional aos algoritmos.

Depois o projeto virou peça de portfólio: evidência mensurável, decisões registradas em ADRs,
verificação e um laboratório que qualquer pessoa abre sem instalar nada. Ele também complementa o
trabalho de IA aplicada do autor, mostrando engenharia de software "convencional" — domínio,
transações, algoritmos e trade-offs.

"Reduzir o escopo" significou remover infraestrutura (Docker e WSL não são pré-requisitos para rodar
ou demonstrar), não funcionalidade. E o iFood veio depois: o projeto não foi feito para o processo
seletivo; a afinidade de domínio foi uma coincidência que o tornou especialmente relevante.

O desenvolvimento é assistido por IA (Command Code), com revisão humana, commits com trailer de
coautoria e todos os números gerados pelo harness — não escritos à mão.
