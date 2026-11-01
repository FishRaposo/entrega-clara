# PostgreSQL, outbox worker and metrics

Memory remains the default. This runbook covers the opt-in persistent mode, the
outbox worker, and the two metric views.

## Options for a database

### Docker Compose (normal path)

```bash
docker compose up -d db
export PERSISTENCE_MODE=postgres
export DATABASE_URL='postgresql+psycopg://delivery:delivery@localhost:5432/delivery'
pip install -e "app/backend[postgres]"
```

### Portable server (used to verify this repository without Docker)

Verified with PostgreSQL 16.9 binaries on Windows:

```powershell
# 1. Download the binaries (about 300 MB) and extract only the server dirs.
#    Extracting everything fails on Windows' path limit because of pgAdmin.
python scripts/data/extract_pg.py postgres.zip C:\pg        # or any zip tool
& C:\pg\pgsql\bin\initdb.exe -D C:\pg\data -U postgres --auth=trust -E UTF8 --locale=C
& C:\pg\pgsql\bin\postgres.exe -D C:\pg\data -p 55432       # keep this running

# 2. In another shell:
& C:\pg\pgsql\bin\createdb.exe -p 55432 -U postgres delivery
$env:DATABASE_URL = 'postgresql+psycopg://postgres@localhost:55432/delivery'
```

## Running the API against it

```bash
export PERSISTENCE_MODE=postgres
python -m uvicorn delivery_platform.api.main:app --port 8000
```

On boot the application applies the schema (idempotent DDL in
`adapters/postgres/store.py`), loads the snapshot, seeds reference data and
persists the seeded snapshot once. A missing driver, URL or server fails with a
precise message; memory mode never touches any of this.

## Outbox worker

```bash
python scripts/worker.py --once          # drain once (useful in tests/CI)
python scripts/worker.py --interval 5    # keep draining
```

It drains pending rows: logs each event id, calls the optional publisher, and marks the row
delivered. The API already publishes in-process after commit; the worker is the recovery path for
the commit → publish window, and `drain_once(..., publish=...)` is where a real subscriber attaches.

## Metrics

| View | Path | Shape |
| --- | --- | --- |
| Prometheus scrape | `GET /metrics` | text exposition (counters, gauges, histograms) |
| Operations panel | `GET /api/v1/operations/metrics` | product counters + the same process metrics as JSON |

Families: `entrega_http_requests_total`, `entrega_http_request_seconds`,
`entrega_routing_queries_total`, `entrega_routing_seconds`,
`entrega_routing_nodes_expanded_total`, `entrega_events_published_total`,
`entrega_event_lag_seconds`, `entrega_sse_connections`.

The registry is **process-local**: counters reset on restart and are not
aggregated across workers. That is the honest scope of an in-process registry.

## Verification

```bash
# Contract suite, both adapters (PostgreSQL cases skip without DATABASE_URL):
DATABASE_URL=postgresql+psycopg://postgres@localhost:55432/delivery \
  python -m pytest tests/repo/test_persistence_contract.py -q

# Full suite in persistent mode is not the default: API tests assume isolated
# seeded state, so they run against the memory adapter.

# Smoke: connectivity, schema and the persisted snapshot.
python scripts/check_postgres.py
```

The full restart smoke (place an order, rebuild the application, read the order
back) lives in `docs/verification.md`; it is what the local verification run
executed against this server.

## Operational notes

* One writer process. Concurrent writers with different unit-of-work lifetimes
  get a `version_conflict` instead of silent overwrites; multi-process support is
  the row-per-aggregate step recorded in ADR 0012.
* The snapshot row is the whole store; fine for demo data, not for large
  production tables.
* Do not point `PERSISTENCE_MODE=postgres` at a database you care about: the
  demo seeds and rewrites its snapshot.
