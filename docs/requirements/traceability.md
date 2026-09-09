# Requirement traceability

The [seed design](../superpowers/specs/2026-08-29-food-delivery-platform-seed-design.md) is the governing specification. This table reproduces every source requirement and maps it to a product surface, acceptance evidence, and its linked dependencies. `—` means the seed design defines no linked requirement identifier.

## Milestone 1 interpretation

The table below is the full product requirement set, not a claim that every requirement belongs in M1. The current [M1 core delivery-loop design](../superpowers/specs/2026-09-01-milestone-1-core-delivery-loop-design.md) includes the operational path through `delivered`, while reviews/ratings, support/chat, real authentication, real providers, and multi-delivery optimization remain deferred. The [platform evolution roadmap](../roadmap/platform-evolution.md) records the enabling order for those later capabilities.

| M1 treatment | Requirements |
| --- | --- |
| Core delivery loop | RF01, RF02, RF03, RF05, RF06, RF08, RF09, RF10, RF13, RF14 |
| Core boundary/subset | RF07, RF12, RNF01, RNF02, RNF03, RNF04, RNF05, RNF06, RNF07, RNF08, RNF09, RNF10 |
| Deferred beyond M1 | RF04, RF11 |

## Functional requirements

| ID | Requirement name | Product surface | Acceptance evidence | Linked dependency identifiers |
| --- | --- | --- | --- | --- |
| RF01 | Pesquisa de Restaurantes e Pratos | Customer discovery | Customer searches, filters, and opens a result | RNF03, RNF05 |
| RF02 | Realização de Pedidos | Customer checkout | Complete order flow | RF12, RNF02, RNF05 |
| RF03 | Acompanhamento em Tempo Real | Customer active-order tracking | Customer tracks the lunch-rush order | RNF01, RNF03 |
| RF04 | Feedback e Avaliação | Customer ratings | Post-delivery rating flow | RNF05 |
| RF05 | Processamento de Pagamentos | Customer checkout / payment adapter | Successful and declined simulated payments | RNF01, RF12, RNF02 |
| RF06 | Painel para Restaurantes | Restaurant operations | Restaurant accepts and prepares an order | RNF01, RNF04 |
| RF07 | Perfil do Usuário | Customer profile | Customer profile and history screens | RF12, RF14 |
| RF08 | Painel do Entregador | Courier operations | Courier completes the assigned route | RNF01, RNF03, RNF04 |
| RF09 | Sistema de Notificações | Notifications | Status and promotional notification events | RNF01 |
| RF10 | Gestão de Cupons | Customer checkout | Valid and invalid checkout cases | RF02, RNF05 |
| RF11 | Suporte e Chat | Customer support / admin support queue | Customer opens and continues a support thread | RNF01, RNF10 |
| RF12 | Segurança de Dados | Cross-cutting security | Security notes, tests, and safe failure states | RF14, RNF08 |
| RF13 | Logs de Auditoria | Admin operations | Admin reviews an order’s history | RNF02, RF14 |
| RF14 | Controle de Acessos | Role-specific navigation and authorization | Role-specific navigation and authorization tests | — (Security foundation) |

## Non-functional requirements

| ID | Requirement name | Product surface | Acceptance evidence | Linked dependency identifiers |
| --- | --- | --- | --- | --- |
| RNF01 | Disponibilidade: 99.9% | Platform operations | Health checks, isolated adapters, graceful degraded states, demo reset, and a documented target; no measured production-uptime claim | — |
| RNF02 | Missing in source document | Order, payment, delivery, and audit state | Validated, idempotent where needed, atomically recorded state changes | — |
| RNF03 | Desempenho: map delay up to 5 seconds | Customer tracking / courier GPS simulator | GPS simulator, last-update indicator, latency metrics, and an acceptance test for tracking updates | — |
| RNF04 | Escalabilidade during peaks | Platform operations | Pagination, caching boundaries, asynchronous event handling, queue-ready interfaces, and a peak-demand simulation | — |
| RNF05 | Usabilidade | Customer, restaurant, and courier experiences | Short checkout, clear status language, task-oriented dashboards, consistent loading states, and frictionless rating flow | — |
| RNF06 | Android and iOS compatibility | Responsive web application | Mobile-first responsive web application and PWA behavior tested at mobile viewports | — |
| RNF07 | Accessibility | All web surfaces | Semantic controls, keyboard operation, focus states, screen-reader labels, contrast checks, motion reduction, and automated accessibility scans | — |
| RNF08 | Conformidade LGPD | Privacy and account controls | Data minimization, consent and privacy surfaces, transparent data use, export/delete demonstration, and retention rules | — |
| RNF09 | Backup and recoverability | Demo data and operations | Seed snapshots, demo export/import, reproducible reset, database backup documentation, and recovery verification | — |
| RNF10 | Friendly errors | All product surfaces | Domain errors translated into user-facing messages without stack traces, internal codes, or infrastructure details | — |

## Scaffold verification status

The current scaffold provides local evidence for its repository boundaries, seed validity, requirement identifier coverage, application-source containment, backend health and demo contracts, routing contracts, and web type/build/test checks. The matrix above remains the source of truth for product acceptance evidence; a passing scaffold check is not a claim that every product surface is complete or production-certified.

The release runbook distinguishes checks verified in the current local environment from Docker Compose checks that are unavailable locally. Payments, location movement, provider notifications, and role access remain simulated. The Toronto international example consistently uses Canadian identity, locale, currency, address, privacy, and time-zone values.
