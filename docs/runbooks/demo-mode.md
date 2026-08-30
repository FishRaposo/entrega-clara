# Demo mode

Demo mode is a deterministic, staged-runtime walkthrough based on `data/scenarios/lunch-rush.json`. It is designed for repeatable portfolio demonstrations and does not depend on real payments, live GPS hardware, map-provider requests, notification-provider credentials, or production accounts.

## Start and inspect

Start the local stack with `make dev`. Confirm the backend is healthy, then inspect the current scenario:

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/demo/scenario
```

## Reset

Reset the in-memory API scenario to the seeded initial state:

```bash
curl -X POST http://localhost:8000/api/v1/demo/reset
```

Reset the running API from the repository root with:

```bash
make demo-reset
```

If the API is offline and you only need to inspect the seed's initial state, run `make demo-preview`. Preview mode reads the seed without changing the source file and does not claim to reset a running scenario.

## Advance and replay

Advance one to ten deterministic events per request. For example, advance one event:

```bash
curl -X POST http://localhost:8000/api/v1/demo/advance \
  -H 'Content-Type: application/json' \
  -d '{"event_count": 1}'
```

To replay a walkthrough, reset and repeat the same advance requests in the same order. The same seed and event sequence produce the same scenario snapshots. A request beyond the remaining events returns a conflict response; reset before starting another replay.

## Switch roles

Open `http://localhost:3000` and use the role navigation to view the Customer, Restaurant, Courier, and Admin demo surfaces. These links are not authentication and do not grant access to real systems. Demo Mode uses the same-origin `/api` proxy to inspect, advance, and reset the deterministic backend scenario.

## Limitations to state during a demo

Use this language when presenting the system: “Payments and location movement are simulated. Map data may be seeded or generalized, notifications are not sent through a real provider, and the role switcher is not authentication. The stack is a local portfolio demonstration and makes no claim of production certification or measured uptime.”
