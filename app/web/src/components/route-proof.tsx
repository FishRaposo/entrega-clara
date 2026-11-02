import { boundsOf, createProjection } from "../lib/projection";

type RouteProofTrace = {
  nodes: number[][];
  origin: number;
  destination: number;
  solvers: {
    alt: { node_path: number[]; expanded_order: number[] };
    dijkstra: { expanded_order: number[] };
  };
};

type RouteProofProps = {
  trace: RouteProofTrace;
};

export function RouteProof({ trace }: RouteProofProps) {
  const node = (index: number) => trace.nodes[index];
  const path = trace.solvers.alt.node_path.map(node);
  const expanded = trace.solvers.dijkstra.expanded_order.map(node);
  const points = [...path, ...expanded, node(trace.origin), node(trace.destination)];
  const projection = createProjection(
    boundsOf(points.map(([latitude, longitude]) => ({ latitude, longitude }))),
    { width: 640, height: 380, padding: 0.1 },
  );
  const project = ([latitude, longitude]: number[]): [number, number] =>
    projection.project(latitude, longitude);

  const pathData = path
    .map((point, index) => {
      const [x, y] = project(point);
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const [originX, originY] = project(node(trace.origin));
  const [destinationX, destinationY] = project(node(trace.destination));

  return (
    <svg
      className="route-proof"
      viewBox="0 0 640 380"
      role="img"
      aria-label={`Rota de demonstração no centro de São Paulo. O Dijkstra abriu ${expanded.length} nós; o A* + ALT abriu ${trace.solvers.alt.expanded_order.length}. A linha verde é o caminho comum; A é a origem e B o destino.`}
    >
      <rect width="640" height="380" fill="#0f1720" />
      {expanded.map(([latitude, longitude], index) => {
        const [x, y] = project([latitude, longitude]);
        return (
          <circle
            key={`${index}-${latitude}-${longitude}`}
            cx={x}
            cy={y}
            r={2.4}
            fill="#d9a441"
            opacity={0.55}
          />
        );
      })}
      <path
        d={pathData}
        fill="none"
        stroke="#8ee08a"
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={originX} cy={originY} r={6} fill="#ffffff" stroke="#0f1720" strokeWidth={2} />
      <text x={originX + 10} y={originY - 8} fill="#ffffff" fontSize={13} fontWeight={700}>
        A
      </text>
      <circle
        cx={destinationX}
        cy={destinationY}
        r={6}
        fill="#b94a22"
        stroke="#0f1720"
        strokeWidth={2}
      />
      <text
        x={destinationX + 10}
        y={destinationY - 8}
        fill="#ffffff"
        fontSize={13}
        fontWeight={700}
      >
        B
      </text>
    </svg>
  );
}
