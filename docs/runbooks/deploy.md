# Deploying the demo

Three independent pieces, no secrets in the repository:

| Piece | Target | Artifact |
| --- | --- | --- |
| API | Fly.io (container) | `Dockerfile`, `fly.toml` |
| Web | Vercel (Next.js) | `app/web/vercel.json` |
| Static lab | GitHub Pages | `.github/workflows/pages.yml`, `site/` |

Nothing here is deployed by the repository's CI. Each command below is an
operator action.

## API on Fly.io

```bash
fly launch --no-deploy --copy-config --name entrega-clara-api --region gru
fly deploy

# Persistent mode (optional):
fly postgres create --name entrega-clara-db --region gru
fly postgres attach entrega-clara-db            # sets DATABASE_URL
fly secrets set PERSISTENCE_MODE=postgres
fly deploy
```

Notes:

* `fly.toml` defaults to `PERSISTENCE_MODE=memory`, so the first deploy needs no
  database. The image installs the `[postgres]` extra, so switching only needs
  the two settings above.
* The image runs migrations on boot (`PostgresStore.migrate`, idempotent DDL).
* Health: `GET /api/v1/health`; metrics: `GET /metrics`.
* The demo seeds reference data at boot. Do not point it at a database you care
  about (ADR 0012).
* The outbox worker is a second process:

  ```bash
  fly ssh console -C "python scripts/worker.py --interval 5"
  ```

  or a separate machine with that command as its entrypoint.

## Web on Vercel

Project root: `app/web`. Environment variable:

```
API_INTERNAL_BASE_URL=https://entrega-clara-api.fly.dev
```

The Next rewrite proxies `/api/*` server-side, so the browser always calls the
same origin (no CORS, no hard-coded backend URL in client code).

## Static lab on GitHub Pages

`site/index.html` is generated (never hand-edited):

```bash
python scripts/media/export_static_lab.py
```

Enable Pages with "GitHub Actions" as the source. The workflow uploads `site/`
on pushes that touch it. The page has no network dependencies: it replays
committed traces, computes the day curve from the committed traffic profile and
prints the published TSP table.

`python scripts/media/check_static_lab.py` fails when the committed page is
stale relative to its sources; `scripts/check.py` runs it as a gate.

## What this deployment is not

* No real payments, identity provider, traffic feed or map tiles.
* No multi-process writes: the PostgreSQL adapter is single-writer by design
  (ADR 0012) and the outbox exists to make the commit → publish window safe, not
  to build a scheduling system.
* No autoscaling story. Two API machines would each keep their own in-process
  metrics and event hub.
