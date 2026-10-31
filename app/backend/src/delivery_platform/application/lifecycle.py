"""Lifecycle recording: audit, notification, and domain-event intent.

Command handlers use this helper inside the unit of work so that every
successful lifecycle mutation produces an audit event, relevant notifications,
and a committed domain event — atomically, published only after commit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from delivery_platform.application.context import CommandContext
from delivery_platform.application.ports import Clock, IdGenerator, UnitOfWork
from delivery_platform.domain.entities import AuditEvent, Notification
from delivery_platform.domain.events import DomainEvent, EventType


@dataclass
class LifecycleRecorder:
    uow: UnitOfWork
    ctx: CommandContext
    clock: Clock
    ids: IdGenerator
    _pending_events: list[DomainEvent] = field(default_factory=list)

    @property
    def pending_events(self) -> list[DomainEvent]:
        return self._pending_events

    def event(
        self,
        event_type: EventType | str,
        *,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        payload_version: int = 1,
        scenario_id: str | None = None,
    ) -> DomainEvent:
        if scenario_id is None:
            scenario_id = self.ctx.scenario_id
        if scenario_id is not None:
            payload = {**payload, "_scenario_id": scenario_id}
        event = self.uow.event_log.append(
            DomainEvent(
                id=self.ids.new_id("evt"),
                type=str(event_type),
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                actor_id=self.ctx.identity.identity_id,
                actor_role=self.ctx.identity.role,
                correlation_id=self.ctx.correlation_id,
                sequence=0,  # assigned by the event log
                occurred_at=self.clock.now(),
                payload_version=payload_version,
                payload=payload,
            )
        )
        self._pending_events.append(event)
        return event

    def audit(
        self,
        action: str,
        *,
        target_type: str,
        target_id: str,
        detail: str,
        scenario_id: str | None = None,
    ) -> AuditEvent:
        if scenario_id is None:
            scenario_id = self.ctx.scenario_id
        audit = AuditEvent(
            id=self.ids.new_id("aud"),
            actor_id=self.ctx.identity.identity_id,
            actor_role=self.ctx.identity.role,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
            correlation_id=self.ctx.correlation_id,
            occurred_at=self.clock.now(),
            scenario_id=scenario_id,
        )
        self.uow.audit_events.add(audit)
        self.event(
            EventType.AUDIT_RECORDED,
            aggregate_type=target_type,
            aggregate_id=target_id,
            payload={"action": action},
            scenario_id=scenario_id,
        )
        return audit

    def notify(
        self,
        recipient_id: str,
        message: str,
        *,
        order_id: str,
        notification_type: str = "order_update",
        scenario_id: str | None = None,
    ) -> Notification:
        if scenario_id is None:
            scenario_id = self.ctx.scenario_id
        notification = Notification(
            id=self.ids.new_id("ntf"),
            recipient_id=recipient_id,
            order_id=order_id,
            type=notification_type,
            message=message,
            created_at=self.clock.now(),
            scenario_id=scenario_id,
        )
        self.uow.notifications.add(notification)
        self.event(
            EventType.NOTIFICATION_CREATED,
            aggregate_type="order",
            aggregate_id=order_id,
            payload={"notification_id": notification.id, "recipient_id": recipient_id},
            scenario_id=scenario_id,
        )
        return notification
