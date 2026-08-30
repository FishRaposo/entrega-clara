# Backend

The FastAPI backend source lives in `src/`. It currently exposes a stable, demo-safe health
boundary at `GET /api/v1/health`.

Run the focused health check locally from the repository root:

```bash
PYTHONPATH=app/backend/src python -m pytest tests/api/test_health.py -q
```

This scaffold is intended for local development and the portfolio demo; it does not claim
production readiness.
