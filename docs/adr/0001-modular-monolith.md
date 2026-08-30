# ADR 0001: Start as a modular monolith

## Status

Accepted — 2026-08-29

## Context

The portfolio needs one coherent customer-to-delivery demo with domain state shared across marketplace, restaurant, courier, administration, notifications, payments, audit, and routing concerns. Early microservices would add deployment and consistency complexity without improving the evidence the project needs to present.

## Decision

Build the backend as a modular monolith under `app/backend/src`. Keep domain boundaries explicit and integration points adapter-oriented so simulated payments, notifications, routing, and persistence can later be replaced independently. The web experience remains under `app/web`.

## Consequences

The initial system can demonstrate atomic state changes and a deterministic demo with straightforward local setup. Module boundaries, interfaces, tests, and observability must be maintained so a future extraction is possible where it becomes justified.
