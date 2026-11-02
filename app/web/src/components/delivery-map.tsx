import type { RoutePlan, RouteStop } from "../lib/api-types";
import { createProjection } from "../lib/projection";

type DeliveryMapProps = {
  route: RoutePlan | null;
  lastKnown?: { latitude: number; longitude: number } | null;
  showSolver?: boolean;
};

const markerFor = (kind: string) =>
  kind === "pickup" ? "#b94a22" : kind === "dropoff" ? "#1b4927" : "#0b66c3";

export function RouteStopList({ stops }: { stops: RouteStop[] }) {
  if (stops.length === 0) {
    return null;
  }
  return (
    <ol className="map-stops" aria-label="Paradas da rota">
      {stops.map((stop) => (
        <li key={`stop-${stop.kind}-${stop.ref_id}`}>
          <span
            className="stop-index"
            style={{ backgroundColor: markerFor(stop.kind) }}
            aria-hidden="true"
          >
            {stop.sequence}
          </span>
          <span>
            <span className="stop-kind">
              {stop.kind === "pickup" ? "Retirada" : "Entrega"}
            </span>{" "}
            · {stop.label}
          </span>
        </li>
      ))}
    </ol>
  );
}

/**
 * Deterministic SVG fallback map — renders the route polyline and stops
 * projected into a local bounding box. No tile provider or API key needed.
 *
 * A MapLibre GL adapter is a documented future expansion (needs `maplibre-gl`
 * plus a tile key); this component is the zero-dependency baseline that the
 * adapter would replace behind the same props.
 */
export function DeliveryMap({ route, lastKnown, showSolver = false }: DeliveryMapProps) {
  const coordinates = route?.geometry?.coordinates ?? [];
  const stops = route?.stops ?? [];

  const points: [number, number][] = [
    ...coordinates,
    ...stops.map((s): [number, number] => [s.longitude, s.latitude]),
    ...(lastKnown ? [[lastKnown.longitude, lastKnown.latitude] as [number, number]] : []),
  ];

  if (points.length === 0) {
    return (
      <div className="delivery-map delivery-map-empty" role="img" aria-label="Mapa sem rota">
        <p>Rota ainda não calculada.</p>
      </div>
    );
  }

  const lngs = points.map((p) => p[0]);
  const lats = points.map((p) => p[1]);
  const W = 640;
  const H = 400;

  const projection = createProjection(
    {
      minLatitude: Math.min(...lats),
      maxLatitude: Math.max(...lats),
      minLongitude: Math.min(...lngs),
      maxLongitude: Math.max(...lngs),
    },
    { width: W, height: H },
  );

  const project = ([lng, lat]: [number, number]): [number, number] =>
    projection.project(lat, lng);

  const pathData = coordinates
    .map((coord, i) => {
      const [x, y] = project(coord);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <figure className="delivery-map" aria-label="Mapa da rota de entrega">
      {stops.length > 0 || lastKnown ? (
        <ul className="map-legend" aria-label="Legenda do mapa">
          {stops.some((stop) => stop.kind === "pickup") ? (
            <li><span className="legend-dot pickup" aria-hidden="true" /> Retirada</li>
          ) : null}
          {stops.some((stop) => stop.kind !== "pickup") ? (
            <li><span className="legend-dot dropoff" aria-hidden="true" /> Entrega</li>
          ) : null}
          {lastKnown ? (
            <li><span className="legend-dot courier" aria-hidden="true" /> Entregador</li>
          ) : null}
        </ul>
      ) : null}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Trajeto entre retirada e entrega; paradas numeradas${lastKnown ? "; entregador na posição atual" : ""}`}
      >
        <rect width={W} height={H} fill="#f1f5ed" />
        {pathData ? (
          <path d={pathData} fill="none" stroke="#0b66c3" strokeWidth={4} strokeLinecap="round" />
        ) : null}
        {stops.map((stop) => {
          const [x, y] = project([stop.longitude, stop.latitude]);
          return (
            <g key={`${stop.kind}-${stop.ref_id}`}>
              <circle cx={x} cy={y} r={10} fill={markerFor(stop.kind)} stroke="#fff" strokeWidth={2} />
              <text
                x={x}
                y={y + 4}
                textAnchor="middle"
                fontSize={11}
                fontWeight={700}
                fill="#fff"
              >
                {stop.sequence}
              </text>
            </g>
          );
        })}
        {lastKnown
          ? (() => {
              const [x, y] = project([lastKnown.longitude, lastKnown.latitude]);
              return (
                <g>
                  <circle cx={x} cy={y} r={7} fill="#12231b" />
                  <circle cx={x} cy={y} r={12} fill="none" stroke="#12231b" strokeOpacity={0.3} />
                </g>
              );
            })()
          : null}
      </svg>
      {route ? (
        <figcaption className="quiet">
          {(route.distance_meters / 1000).toFixed(1)} km · ~
          {Math.max(1, Math.round(route.estimated_seconds / 60))} min ·{" "}
          {route.objective === "time" ? "rota mais rápida" : "rota mais curta"}
          {showSolver
            ? ` · solver ${route.solver_name} v${route.solver_version} · mapa determinístico (fallback)`
            : ""}
        </figcaption>
      ) : null}
    </figure>
  );
}
