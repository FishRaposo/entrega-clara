# ADR 0005: SSE for one-way M1 realtime updates

## Status

Accepted for Milestone 1.

## Context

Customer tracking, order status, notifications, and Demo Mode need server-to-browser updates. M1 commands are discrete HTTP actions initiated by a role surface. The application does not need browser-to-server arbitrary messaging, binary frames, or a multi-user collaboration protocol.

The current scaffold has no realtime transport. The architecture must support a convincing live experience without making a broker or WebSocket fleet a prerequisite for the first vertical slice.

## Decision

Use ordinary versioned REST endpoints for commands and Server-Sent Events for authorized server-to-client updates.

The stream endpoint is:

```text
GET /api/v1/orders/{order_id}/stream
```

On connection it sends a current order/tracking snapshot, then new events. Each event has a stable ID, event name, versioned payload, aggregate identity, actor/correlation metadata, sequence, and UTC timestamp. The browser uses `EventSource`. The server sends a heartbeat and closes cleanly when the client disconnects.

Events are published only after the command transaction commits. M1 uses an in-process event hub. Reconnection may use `Last-Event-ID`, but the client still refetches the authoritative snapshot because M1 does not promise durable event replay.

## Consequences

### Positive

- Simple fit for one-way updates and browser support.
- Commands remain easy to authorize, validate, retry, and test.
- No WebSocket protocol or broker is required for the first vertical slice.
- The same event envelope can later feed notifications, audit projections, and a durable outbox.
- The UI has a clear degraded path: snapshot polling/manual refresh when a stream is unavailable.

### Costs and risks

- In-process subscriptions do not scale across API replicas.
- A crash after database commit but before publication can lose a live notification.
- Connection limits, proxy buffering, keepalives, and cleanup need operational tests.
- The browser still needs snapshot/refetch logic and must not assume every event arrives.

## Rejected alternatives

| Alternative | Reason not selected for M1 |
| --- | --- |
| Polling only | Simpler but less convincing for tracking and adds repeated request load |
| WebSockets | More bidirectional protocol complexity than M1 needs |
| Durable broker first | Adds infrastructure before the single-process product flow is proven |
| SSE as source of truth | A stream is a delivery mechanism; current persisted state remains authoritative |

## Implementation guardrails

- Authorize each stream before subscribing.
- Never stream another customer's address/location/audit data.
- Use `id`, `event`, `data`, and agreed retry/heartbeat behavior.
- Keep database sessions out of the long-lived stream.
- On reconnect, refetch the snapshot and reconcile sequence/version.
- Record event IDs and correlation IDs for test/debug visibility.
- Introduce a transactional outbox before multiple API processes or external notification workers.
- Consumers must tolerate duplicate events.

## References

- [FastAPI SSE tutorial](https://fastapi.tiangolo.com/tutorial/server-sent-events/)
- [FastAPI SSE reference](https://fastapi.tiangolo.com/reference/sse/)
- [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [MDN Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [Redis Streams](https://redis.io/docs/latest/develop/data-types/streams/)
