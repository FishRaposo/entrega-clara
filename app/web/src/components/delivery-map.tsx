import type { RoutePlan } from "../lib/api-types";

type DeliveryMapProps = {
  route: RoutePlan | null;
  lastKnown?: { latitude: number; longitude: number } | null;
};

/**
 * Deterministic SVG fallback map — renders the route polyline and stops
 * projected into a local bounding box. No tile provider or API key needed.
 *
 * A MapLibre GL adapter is a documented future expansion (needs `maplibre-gl`
 * plus a tile key); this component is the zero-dependency baseline that the
 * adapter would replace behind the same props.
 */
export function DeliveryMap({ route, lastKnown }: DeliveryMapProps) {
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
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const padLng = Math.max((maxLng - minLng) * 0.08, 0.001);
  const padLat = Math.max((maxLat - minLat) * 0.08, 0.001);
  const W = 640;
  const H = 400;

  const project = ([lng, lat]: [number, number]): [number, number] => [
    ((lng - (minLng - padLng)) / (maxLng - minLng + 2 * padLng)) * W,
    H - ((lat - (minLat - padLat)) / (maxLat - minLat + 2 * padLat)) * H,
  ];

  const pathData = coordinates
    .map((coord, i) => {
      const [x, y] = project(coord);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const markerFor = (kind: string) =>
    kind === "pickup" ? "#b94a22" : kind === "dropoff" ? "#1b4927" : "#0b66c3";

  return (
    <figure className="delivery-map" aria-label="Mapa da rota de entrega">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Trajeto entre retirada e entrega">
        <rect width={W} height={H} fill="#f1f5ed" />
        {pathData ? (
          <path d={pathData} fill="none" stroke="#0b66c3" strokeWidth={4} strokeLinecap="round" />
        ) : null}
        {stops.map((stop) => {
          const [x, y] = project([stop.longitude, stop.latitude]);
          return (
            <g key={`${stop.kind}-${stop.ref_id}`}>
              <circle cx={x} cy={y} r={9} fill={markerFor(stop.kind)} stroke="#fff" strokeWidth={2} />
              <text x={x + 14} y={y + 5} fontSize={13} fill="#12231b">
                {stop.label}
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
                  <text x={x + 16} y={y - 8} fontSize={12} fill="#12231b">
                    Entregador
                  </text>
                </g>
              );
            })()
          : null}
      </svg>
      {route ? (
        <figcaption className="quiet">
          {(route.distance_meters / 1000).toFixed(1)} km · ~
          {Math.max(1, Math.round(route.estimated_seconds / 60))} min ·{" "}
          {route.objective === "time" ? "rota mais rápida" : "rota mais curta"} · solver{" "}
          {route.solver_name} v{route.solver_version} · mapa determinístico (fallback)
        </figcaption>
      ) : null}
    </figure>
  );
}
