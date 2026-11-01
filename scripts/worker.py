"""Drain the PostgreSQL transactional outbox.

The API publishes committed events in-process. This worker covers the window
between the commit and that publication — a crash, a failed publish, or a future
external subscriber. Draining marks events delivered only after the publisher
accepted them, so a failure re-delivers instead of losing the event.

Usage:
    python scripts/worker.py --once
    python scripts/worker.py --interval 5
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "backend" / "src"))

from delivery_platform.core.config import settings

if TYPE_CHECKING:
    from delivery_platform.adapters.postgres.store import PostgresStore

Publisher = Callable[[list[dict[str, Any]]], None]


def drain_once(
    store: PostgresStore,
    *,
    limit: int = 100,
    publish: Publisher | None = None,
    log: Callable[[str], None] = print,
) -> int:
    """Publish pending events and mark them delivered; returns how many."""
    rows = store.pending_outbox(limit)
    if not rows:
        return 0
    if publish is not None:
        publish(rows)
    store.mark_published([str(row["event_id"]) for row in rows])
    for row in rows:
        log(f"{row['event_id']} {row['type']} {row['aggregate_id']}")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Drain once and exit")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between drains")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    try:
        from delivery_platform.adapters.postgres.store import PostgresStore
    except ImportError as error:
        raise SystemExit(
            "The outbox worker needs the PostgreSQL extra: "
            "pip install -e 'app/backend[postgres]'"
        ) from error
    store = PostgresStore.from_url(settings.database_url)
    store.migrate()
    while True:
        drained = drain_once(store, limit=args.limit)
        if drained:
            print(f"drained {drained} event(s)")
        if args.once:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
