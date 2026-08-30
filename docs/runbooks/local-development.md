# Local development

This repository is a staged runtime for a deterministic portfolio demo. It is not a production deployment and must not be configured with real payment, GPS, map, or notification credentials.

## Prerequisites

- Python 3.11
- Node 22
- Docker Compose

## Run the quality gate

Install the declared development dependencies and run the complete local gate:

```bash
make install
make check
```

`make check` validates the lunch-rush seed and requirements traceability, checks the `app/` source boundary, then runs backend and frontend linting, type checks, and tests.

## Start the local stack

Run the Compose stack:

```bash
make dev
```

Compose starts the services named `db`, `api`, and `web`. The API is available at `http://localhost:8000`, including `GET /api/v1/health`; the web shell is available at `http://localhost:3000`. Browser requests use same-origin `/api/...` paths, and Next.js forwards them to `http://api:8000` inside the Compose network.

The local database uses the fixed `delivery` development account specified in `docker-compose.yml`. It is demo-only. The root image copies only `app/backend` and `data`; it does not copy `.env` files or other secrets into the image.

Validate the resolved Compose contract without starting containers:

```bash
docker compose config
```

## Non-production boundary

Payments are simulated, GPS movement is simulated, map data may be seeded or generalized, and notifications have no provider credentials. Role navigation is a demo aid, not authentication or identity verification. This project does not claim payment certification, production compliance, real courier operations, or measured uptime.
