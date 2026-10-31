"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getLabGraph,
  runLabPath,
  runLabTsp,
  type LabGraph,
  type LabPathResult,
  type LabTspResult,
} from "../lib/api-client";
import { DEMO_IDENTITIES } from "../lib/identities";

const IDENTITY = DEMO_IDENTITIES.operations;

function project(graph: LabGraph) {
  const lats = graph.nodes.map((n) => n.latitude);
  const lons = graph.nodes.map((n) => n.longitude);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const pad = 20;
  const w = 640 - pad * 2;
  const h = 420 - pad * 2;
  return (lat: number, lon: number): [number, number] => [
    pad + ((lon - minLon) / (maxLon - minLon || 1)) * w,
    pad + (1 - (lat - minLat) / (maxLat - minLat || 1)) * h,
  ];
}

export function AlgorithmLab() {
  const [graph, setGraph] = useState<LabGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [origin, setOrigin] = useState<string>("");
  const [destination, setDestination] = useState<string>("");
  const [solver, setSolver] = useState<"astar" | "dijkstra">("astar");
  const [objective, setObjective] = useState<"time" | "distance">("time");
  const [pathResult, setPathResult] = useState<LabPathResult | null>(null);
  const [tspResult, setTspResult] = useState<LabTspResult | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getLabGraph(IDENTITY)
      .then((g) => {
        setGraph(g);
        setOrigin(g.nodes[0]?.id ?? "");
        setDestination(g.nodes[g.nodes.length - 1]?.id ?? "");
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const xy = useMemo(() => (graph ? project(graph) : null), [graph]);
  const nodeById = useMemo(
    () => new Map(graph?.nodes.map((n) => [n.id, n]) ?? []),
    [graph],
  );

  async function runPath() {
    if (!graph) return;
    setBusy(true);
    setError(null);
    try {
      setPathResult(
        await runLabPath(IDENTITY, {
          origin,
          destination,
          solver,
          objective,
          trace: true,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function runTsp() {
    if (!graph) return;
    setBusy(true);
    setError(null);
    try {
      // deterministic pick: every ~6th node, capped by the API's bound
      const picks = graph.nodes
        .filter((_, i) => i % 6 === 0)
        .slice(0, 8)
        .map((n) => n.id);
      setTspResult(
        await runLabTsp(IDENTITY, {
          nodes: picks,
          solver: "two-opt",
          objective,
          origin_index: 0,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const expanded = new Set(pathResult?.expanded_order ?? []);
  const onPath = new Set(pathResult?.node_path ?? []);

  return (
    <section className="panel stack">
      <h2>Laboratório de roteirização</h2>
      <p className="muted">
        O grafo sintético do centro de SP — {graph ? `${graph.nodes.length} nós, ${graph.edges.length} arestas, versão ${graph.version}` : "carregando…"}.
        Compare solvers no mesmo problema, com contadores de trabalho honestos.
      </p>
      {error ? <p role="alert" className="error">{error}</p> : null}

      <div className="lab-controls">
        <label>
          Origem{" "}
          <select value={origin} onChange={(e) => setOrigin(e.target.value)}>
            {graph?.nodes.map((n) => (
              <option key={n.id} value={n.id}>{n.id}</option>
            ))}
          </select>
        </label>
        <label>
          Destino{" "}
          <select value={destination} onChange={(e) => setDestination(e.target.value)}>
            {graph?.nodes.map((n) => (
              <option key={n.id} value={n.id}>{n.id}</option>
            ))}
          </select>
        </label>
        <label>
          Solver{" "}
          <select value={solver} onChange={(e) => setSolver(e.target.value as typeof solver)}>
            <option value="astar">A*</option>
            <option value="dijkstra">Dijkstra</option>
          </select>
        </label>
        <label>
          Objetivo{" "}
          <select value={objective} onChange={(e) => setObjective(e.target.value as typeof objective)}>
            <option value="time">menor tempo</option>
            <option value="distance">menor distância</option>
          </select>
        </label>
        <button type="button" onClick={runPath} disabled={busy || !graph}>
          Executar busca
        </button>
        <button type="button" onClick={runTsp} disabled={busy || !graph}>
          Otimizar 8 paradas (2-opt)
        </button>
      </div>

      {graph && xy ? (
        <svg
          role="img"
          aria-label="Grafo sintético com expansão do solver"
          viewBox="0 0 640 420"
          className="lab-graph"
        >
          {graph.edges.map((e, i) => {
            const a = nodeById.get(e.from);
            const b = nodeById.get(e.to);
            if (!a || !b) return null;
            const [x1, y1] = xy(a.latitude, a.longitude);
            const [x2, y2] = xy(b.latitude, b.longitude);
            return (
              <line
                key={i}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="#2a3550"
                strokeWidth={e.speed_kmh > 30 ? 1.6 : 0.8}
              />
            );
          })}
          {graph.nodes.map((n) => {
            const [x, y] = xy(n.latitude, n.longitude);
            const isPath = onPath.has(n.id);
            const isExpanded = expanded.has(n.id);
            return (
              <circle
                key={n.id}
                cx={x}
                cy={y}
                r={isPath ? 6 : isExpanded ? 4 : 2.5}
                fill={isPath ? "#22c55e" : isExpanded ? "#f59e0b" : "#64748b"}
                opacity={isPath || isExpanded ? 1 : 0.6}
              >
                <title>{n.id}</title>
              </circle>
            );
          })}
        </svg>
      ) : null}

      <div className="lab-results">
        {pathResult ? (
          <div className="panel">
            <h3>Busca ponto-a-ponto</h3>
            <p>
              {pathResult.solver_name}: {pathResult.node_path.length} nós no
              caminho, {pathResult.nodes_expanded} expandidos,{" "}
              {(pathResult.distance_meters / 1000).toFixed(2)} km, ~
              {Math.round(pathResult.estimated_seconds)} s,{" "}
              {(pathResult.computation_time_ns / 1e6).toFixed(2)} ms.
            </p>
            <p className="muted">
              Verde = caminho ótimo · âmbar = nós expandidos durante a busca.
            </p>
          </div>
        ) : null}
        {tspResult ? (
          <div className="panel">
            <h3>Multi-parada (TSP)</h3>
            <p>
              {tspResult.solver_name}: custo {tspResult.total_cost.toFixed(1)} (
              {tspResult.objective === "time" ? "segundos" : "metros"}),{" "}
              {tspResult.routes_evaluated} avaliações,{" "}
              {(tspResult.execution_time_ns / 1e6).toFixed(2)} ms.
            </p>
            <p className="muted">{tspResult.route.join(" → ")}</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
