"""In-process event hub: post-commit publication for SSE subscribers.

Subscribers hold per-order queues; publication happens only after a unit of
work commits. M1 does not promise lossless replay — reconnecting clients
refetch the snapshot.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field

from delivery_platform.domain.events import DomainEvent


@dataclass
class Subscription:
    """One authorized order stream subscription."""

    aggregate_ids: tuple[str, ...]
    _hub: InProcessEventHub
    _queue: queue.Queue[DomainEvent] = field(default_factory=queue.Queue)
    _closed: bool = False

    def next_event(self, timeout_seconds: float) -> DomainEvent | None:
        """Return the next event, or None on heartbeat timeout."""
        try:
            return self._queue.get(timeout=timeout_seconds)
        except queue.Empty:
            return None

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._hub.unsubscribe(self.aggregate_ids, self._queue)


class InProcessEventHub:
    """Routes committed events to authorized per-order subscribers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[queue.Queue[DomainEvent]]] = {}

    def publish(self, events: list[DomainEvent]) -> None:
        with self._lock:
            for event in events:
                for subscriber in self._subscribers.get(event.aggregate_id, []):
                    subscriber.put(event)

    def subscribe(self, aggregate_id: str) -> Subscription:
        return self.subscribe_many((aggregate_id,))

    def subscribe_many(self, aggregate_ids: tuple[str, ...]) -> Subscription:
        subscription = Subscription(aggregate_ids=aggregate_ids, _hub=self)
        with self._lock:
            for aggregate_id in aggregate_ids:
                self._subscribers.setdefault(aggregate_id, []).append(subscription._queue)
        return subscription

    def unsubscribe(
        self, aggregate_ids: tuple[str, ...], subscriber: queue.Queue[DomainEvent]
    ) -> None:
        with self._lock:
            for aggregate_id in aggregate_ids:
                subscribers = self._subscribers.get(aggregate_id, [])
                if subscriber in subscribers:
                    subscribers.remove(subscriber)
