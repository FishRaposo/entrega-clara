# ADR 0004: Local route ownership with provider-neutral map rendering

## Status

Accepted for Milestone 1.

## Context

The portfolio thesis depends on showing how a legacy brute-force route implementation is measured and superseded. If the live courier path delegates all routing to a map vendor, the project cannot explain or measure its own algorithm. At the same time, a real basemap makes the delivery story easier to understand than a disconnected abstract graph.

Map tiles, directions, geocoding, and route optimization are different concerns. They have different cost, data, privacy, and licensing implications.

## Decision

For M1:

- the backend owns route calculation;
- the live route uses deterministic A* over a versioned synthetic graph;
- Dijkstra is a test oracle for bounded route correctness;
- the legacy brute-force TSP remains a historical baseline and is not the live two-leg solver;
- the delivery route is courier → restaurant → customer;
- the backend returns a provider-neutral `RouteResult` with ordered stops, GeoJSON geometry, distance, ETA, solver/version, graph version, and metrics;
- the frontend renders that result through a MapLibre GL adapter;
- MapTiler is the selected basemap/style provider when a restricted browser key is configured;
- the map is optional: missing keys or provider outage show a degraded state while order/tracking remains usable.

The backend never imports MapLibre, MapTiler, or another map SDK. The web application does not calculate business routes or call provider directions directly.

## Consequences

### Positive

- The courier flow demonstrates the project's own algorithmic work.
- The same `RouteResult` can power a live map, static fallback, tests, or another provider.
- Map provider failure does not make the product flow fail.
- Graph and solver versions make route behavior reproducible.
- Future provider comparison can use the same route problem and metrics.

### Costs and risks

- A synthetic graph must be maintained and visually aligned with the map viewport.
- Local distance/ETA is not real street navigation and must be labeled honestly.
- Browser map keys count against provider quotas and require origin restrictions.
- Any OSM-derived graph/data import adds attribution and ODbL review.
- Dynamic rerouting, traffic, geocoding, and real-road accuracy remain later work.

## Rejected alternatives

| Alternative | Reason not selected for M1 |
| --- | --- |
| Provider directions as live authority | Hides the algorithm thesis and makes CI/demo correctness network-dependent |
| Abstract canvas-only map | Less convincing product surface and no real map integration boundary |
| Full road graph in M1 | Adds data licensing, freshness, storage, and operational scope before the core loop exists |
| Web-only route calculation | Duplicates domain logic and makes authorization/metrics/reproducibility weaker |

## Implementation guardrails

- Geometry uses `[longitude, latitude]` consistently at the map boundary.
- Required stops occur once, with pickup before drop-off.
- Route results carry graph and solver versions.
- Route timing excludes network, tile loading, browser rendering, and charting.
- MapTiler attribution is visible.
- Browser keys are restricted; service tokens are backend-only.
- No external map request is required by unit, API, solver, or E2E correctness tests.
- A future road-network import requires a source, license, refresh, attribution, and privacy decision.

## References

- [MapLibre GL JS](https://www.maplibre.org/maplibre-gl-js/docs/)
- [MapLibre GeoJSON sources](https://www.maplibre.org/maplibre-gl-js/docs/API/classes/GeoJSONSource/)
- [MapTiler MapLibre integration](https://docs.maptiler.com/maplibre/)
- [MapTiler API-key security](https://docs.maptiler.com/cloud/api/authentication-key/)
- [MapTiler key protection](https://docs.maptiler.com/guides/maps-apis/maps-platform/how-to-protect-your-map-key)
- [MapTiler authentication](https://docs.maptiler.com/cloud/api/authentication/)
- [MapTiler attribution](https://docs.maptiler.com/guides/map-design/attribution/add-attribution/)
- [OSM Foundation attribution guidelines](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines)
- [OSRM HTTP API](https://project-osrm.org/docs/v26.4.0/http)
