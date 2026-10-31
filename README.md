# Entrega Clara

Entrega Clara is a Brazil-first, internationally extensible food-delivery platform whose distinctive portfolio thesis is making the customer-to-delivery operation visible, measurable, and replaceable from a legacy route baseline. The first milestone ships a real vertical slice: seeded Brazilian catalog, cart and coupons, idempotent checkout with simulated payment, restaurant and courier lifecycle commands, deterministic graph routing, post-commit domain events, authorized SSE tracking, an operations read model, and a guided demo — all running with only Python and Node.

## Para recrutadores (iFood)

Este repositório demonstra, de ponta a ponta e sem dependências externas, o mesmo recorte operacional que um app de delivery resolve em produção: cardápio → sacola → checkout idempotente → fila do restaurante → oferta, coleta, rota e entrega do entregador → rastreamento por SSE → visão de operações.

- **Domínio real, não mock**: os mesmos handlers de comando atendem a API, as telas de papel e o cenário guiado (`data/scenarios/lunch-rush.json`).
- **Invariantes de negócio**: transições de estado válidas, um restaurante por sacola, cupom com validade/mínimo, uma entrega ativa por entregador, posições de GPS monotônicas, autorização por identidade resolvida no servidor.
- **Arquitetura substituível**: portas de aplicação (UoW, pagamento, roteirização, identidade, eventos) isolam os adapters; PostgreSQL, MapLibre/MapTiler, provedores de pagamento e autenticação real são expansões documentadas, não requisitos.
- **Laboratório de roteirização**: A* (objetivo tempo/distância), Dijkstra, Held-Karp, vizinho-mais-próximo e 2-opt comparáveis em `docs/benchmarks/` e na página `/lab`.
- **Qualidade verificável**: 175+ testes de API/domínio (contagem exata em docs/verification.md), lint Ruff, mypy estrito, suíte E2E Playwright com varreduras de acessibilidade (axe), validação de seeds e cobertura de requisitos.
- **Brasil de verdade**: pt-BR, BRL em centavos, PIX, seed de São Paulo, cópia consciente de LGPD.

Comece pelo [guia de desenvolvimento local](docs/runbooks/local-development.md) e pelo [modo demonstração](docs/runbooks/demo-mode.md).

## Primary demo story

Two stories share one code path. Interactively, each role page drives real commands: the customer builds a cart and checks out (idempotent, simulated payment), the restaurant confirms/prepares/marks ready, the courier accepts an offer, picks up, starts the graph-computed route, streams GPS points, and completes the delivery — while the customer watches a live SSE stream and map. The guided lunch-rush scenario replays the same journey step-by-step through those same handlers via Demo Mode, with scoped reset that preserves dynamically created orders.

## Market boundary

Brazil is the default market: `pt-BR`, BRL, PIX, cards, wallets, Brazilian seed geography, and LGPD-aware privacy copy. It is not a Brazil-only design: locale, currency, payment methods, addresses, time zones, legal copy, maps, and notifications remain configuration-driven for future markets. Money uses integer minor units plus currency; time is stored canonically and rendered in the active market time zone.

## Repository layout

| Path | Purpose |
| --- | --- |
| `app/backend/` | FastAPI surface, domain entities/state machine, application commands, memory adapters, routing solvers |
| `app/web/` | pt-BR role surfaces (cliente, restaurante, entregador, operações), SSE client, deterministic map fallback |
| `data/seed/` | Deterministic Brazil reference seed (synthetic, no real personal data) |
| `data/graph/` | Versioned synthetic street graph for A*/Dijkstra route solving |
| `data/scenarios/` | Command-script demo scenarios replayed through real handlers |
| `docs/` | Architecture, ADRs, requirements traceability, runbooks, and governing specifications |
| `scripts/` | Development, demo, validation, and quality automation |
| `tests/` | Backend, frontend, repository, and e2e test suites |

All application source belongs under `app/`.

## Demo access

The local web shell provides working surfaces for Customer (`/customer`), Restaurant (`/restaurant`), Courier (`/courier`), and Operations (`/admin`), plus the guided scenario at `/demo`. Each surface sends a fixed `X-Demo-Identity` header resolved server-side — a demo aid, never real authentication.

## Local setup

Requires only Python 3.11+ and Node 22+ — no Docker, database, `make`, or provider accounts.

1. Copy `.env.example` to `.env` (optional; safe defaults, no credentials needed).
2. Install dependencies:

   ```bash
   python -m pip install -e "app/backend[dev]"
   cd app/web && npm install
   ```

3. Start the API from the repository root:

   ```bash
   uvicorn delivery_platform.api.main:app --port 8000
   ```

4. Start the web shell in a second terminal:

   ```bash
   cd app/web && npm run dev
   ```

5. Open `http://localhost:3000`; the API listens on `http://localhost:8000` (`GET /api/v1/health`).

Docker Compose, PostgreSQL, MapTiler, and external providers are documented future expansions, not requirements — see [external dependencies](docs/architecture/external-dependencies.md).

See the [local development runbook](docs/runbooks/local-development.md) for local URLs and service details, and the [demo-mode runbook](docs/runbooks/demo-mode.md) for deterministic reset, advancement, replay, and role-navigation instructions.

For the next implementation phase, read the [M1 development runbook](docs/runbooks/milestone-1-development.md), the [M1 design](docs/superpowers/specs/2026-09-01-milestone-1-core-delivery-loop-design.md), and the [platform build research](docs/research/2026-09-01-platform-build-research.md). The [platform evolution roadmap](docs/roadmap/platform-evolution.md) records the capabilities intentionally deferred beyond M1.

## Commands

Run from the repository root (the Makefile wraps the same commands when `make` is available):

| Command | Purpose |
| --- | --- |
| `python -m pytest tests -q` | Backend and repository tests |
| `cd app/web && npm test -- --run` | Frontend tests |
| `ruff check app/backend/src tests` | Backend lint |
| `cd app/web && npm run lint` | Frontend lint |
| `mypy app/backend/src` | Backend type check |
| `cd app/web && npm run typecheck` | Frontend type check |
| `python scripts/data/validate_seed.py data/scenarios/lunch-rush.json` | Validate deterministic seed |
| `python scripts/quality/check_requirement_coverage.py docs/requirements/traceability.md` | Requirement coverage |
| `python scripts/repo/check_app_boundary.py` | Application source boundary |
| `python scripts/demo/reset_demo.py` | Reset the running local API scenario |
| `python scripts/demo/reset_demo.py --seed-preview` | Preview the offline seed without contacting the API |
| `cd app/web && npx playwright test` | E2E journey + axe scans (needs `npx playwright install` once) |

The repository smoke test can run before application tooling exists:

```bash
python -m pytest tests/repo/test_repository_layout.py -q
```

## Release and publication status

This scaffold is public at [FishRaposo/entrega-clara](https://github.com/FishRaposo/entrega-clara). It remains a non-production demo platform: follow the [public demo release runbook](docs/runbooks/public-demo-release.md) to reproduce local validation, and record any Docker-unavailable check as unverified rather than passed.

Clone it with:

```bash
git clone https://github.com/FishRaposo/entrega-clara.git
```

## Non-production limitations

This is not a production payment platform, logistics company, or identity provider. The current runtime uses seeded or simulated payment references, roles, GPS updates, notifications, and operational data. It must not process real funds, customer card data, production credentials, real courier identity verification, or live support operations. Availability targets and privacy controls are documented portfolio evidence, not claims of production certification or measured uptime.

The governing product specification is [the seed design](docs/superpowers/specs/2026-08-29-food-delivery-platform-seed-design.md).
