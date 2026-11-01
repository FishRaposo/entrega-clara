"""Check the PostgreSQL adapter: connect, migrate, report the persisted snapshot.

    DATABASE_URL=postgresql+psycopg://... python scripts/check_postgres.py

Exits non-zero with a readable message when the driver, URL or server is
unusable. Never touches the memory-mode demo path.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "backend" / "src"))

from delivery_platform.adapters.postgres.store import (
    PostgresStore,
    PostgresUnavailable,
)
from delivery_platform.core.config import settings


def main() -> int:
    try:
        store = PostgresStore.from_url(settings.database_url)
        store.migrate()
        snapshot, version = store.load()
    except PostgresUnavailable as error:
        print(f"unavailable: {error}")
        return 2
    except Exception as error:  # noqa: BLE001 - driver, network or permission
        print(f"failed: {error}")
        return 1
    collections = {
        "orders": len(snapshot.orders),
        "deliveries": len(snapshot.deliveries),
        "route_plans": len(snapshot.route_plans),
        "events": len(snapshot.event_log),
    }
    pending = len(store.pending_outbox())
    print(f"ok: snapshot version {version}, {collections}, outbox pending {pending}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
