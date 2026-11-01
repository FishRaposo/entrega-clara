"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getLabBenchmarks,
  getLabGraph,
  getLabTraffic,
  runLabPath,
  runLabTsp,
  type LabBenchmarks,
  type LabGraph,
  type LabGraphName,
  type LabPathResult,
  type LabSolverName,
  type LabTraffic,
  type LabTspResult,
} from "../lib/api-client";
import { formatDuration } from "../lib/format";
import { DEMO_IDENTITIES } from "../lib/identities";
import {
  buildFrames,
  compareSolvers,
  nearestNodeIndex,
  pathIndices,
  type TraceFrame,
} from "../lib/lab-trace";
import type { GeoBounds } from "../lib/projection";
import { LabCanvas } from "./lab-canvas";

const IDENTITY = DEMO_IDENTITIES.operations;

const SOLVERS: { value: LabSolverName; label: string; hint: string }[] = [
  { value: "dijkstra", label: "Dijkstra", hint: "oráculo exato, custo uniforme" },
  { value: "astar", label: "A* (linha reta)", hint: "heurística admissível" },
  { value: "alt", label: "A* + ALT", hint: "marcos pré-computados" },
  { value: "bidirectional", label: "Bidirecional + ALT", hint: "duas frentes de busca" },
  {
    value: "ch",
    label: "Hierarquia de contração",
    hint: "pré-processa uma vez, responde em milissegundos",
  },
  { value: "weighted-astar", label: "A* ponderado (ε)", hint: "inexato, no máximo ε× o ótimo" },
];

const DEMO_POINTS = {
  restaurant: { latitude: -23.5482, longitude: -46.6371 },
  customer: { latitude: -23.5515, longitude: -46.632 },
};

type PanelState = {
  solver: LabSolverName;
  epsilon: number;
  result: LabPathResult | null;
};

function graphBounds(graph: LabGraph): GeoBounds {
  let minLatitude = Infinity;
  let maxLatitude = -Infinity;
  let minLongitude = Infinity;
  let maxLongitude = -Infinity;
  for (const [latitude, longitude] of graph.nodes) {
    if (latitude < minLatitude) minLatitude = latitude;
    if (latitude > maxLatitude) maxLatitude = latitude;
    if (longitude < minLongitude) minLongitude = longitude;
    if (longitude > maxLongitude) maxLongitude = longitude;
  }
  return { minLatitude, maxLatitude, minLongitude, maxLongitude };
}

function solverLabel(name: LabSolverName): string {
  return SOLVERS.find((solver) => solver.value === name)?.label ?? name;
}

export function AlgorithmLab() {
  const [graphName, setGraphName] = useState<LabGraphName>("default");
  const [graph, setGraph] = useState<LabGraph | null>(null);
  const [objective, setObjective] = useState<"time" | "distance">("time");
  const [originIndex, setOriginIndex] = useState<number | null>(null);
  const [destinationIndex, setDestinationIndex] = useState<number | null>(null);
  const [pickMode, setPickMode] = useState<"origin" | "destination" | "stops">("origin");
  const [panels, setPanels] = useState<[PanelState, PanelState]>([
    { solver: "dijkstra", epsilon: 2, result: null },
    { solver: "alt", epsilon: 2, result: null },
  ]);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(400);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stops, setStops] = useState<number[]>([]);
  const [tspSolver, setTspSolver] = useState<"held-karp" | "two-opt" | "nearest-neighbor">(
    "two-opt",
  );
  const [tspResult, setTspResult] = useState<LabTspResult | null>(null);
  const [tspReference, setTspReference] = useState<LabTspResult | null>(null);
  const [benchmarks, setBenchmarks] = useState<LabBenchmarks | null>(null);
  const [traffic, setTraffic] = useState<LabTraffic | null>(null);
  const autoRunRef = useRef(false);
  const prefersReducedMotion = useMemo(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true,
    [],
  );

  useEffect(() => {
    let cancelled = false;
    autoRunRef.current = false;
    setGraph(null);
    getLabGraph(IDENTITY, graphName)
      .then((loaded) => {
        if (cancelled) return;
        setGraph(loaded);
        setOriginIndex((current) => (current === null ? 0 : Math.min(current, loaded.node_count - 1)));
        setDestinationIndex((current) =>
          current === null ? loaded.node_count - 1 : Math.min(current, loaded.node_count - 1),
        );
      })
      .catch((cause: Error) => {
        if (!cancelled) setError(cause.message);
      });
    return () => {
      cancelled = true;
    };
  }, [graphName]);

  useEffect(() => {
    getLabBenchmarks(IDENTITY)
      .then(setBenchmarks)
      .catch(() => setBenchmarks(null));
  }, []);

  useEffect(() => {
    if (!graph || originIndex === null || destinationIndex === null) {
      setTraffic(null);
      return;
    }
    let cancelled = false;
    getLabTraffic(
      IDENTITY,
      graph.ids[originIndex],
      graph.ids[destinationIndex],
      graphName,
    )
      .then((loaded) => {
        if (!cancelled) setTraffic(loaded);
      })
      .catch(() => {
        if (!cancelled) setTraffic(null);
      });
    return () => {
      cancelled = true;
    };
  }, [graph, graphName, originIndex, destinationIndex]);

  const indexById = useMemo(
    () => new Map((graph?.ids ?? []).map((id, index) => [id, index])),
    [graph],
  );
  const bounds = useMemo(() => (graph ? graphBounds(graph) : null), [graph]);
  const benchmarkRows = benchmarks?.tsp_graph ?? benchmarks?.tsp_random ?? [];
  const frames = useMemo<[TraceFrame[], TraceFrame[]]>(
    () => [
      buildFrames(
        indexById,
        panels[0].result?.expanded_order ?? [],
        panels[0].result?.frontier_sizes,
        panels[0].result?.expansion_costs,
      ),
      buildFrames(
        indexById,
        panels[1].result?.expanded_order ?? [],
        panels[1].result?.frontier_sizes,
        panels[1].result?.expansion_costs,
      ),
    ],
    [indexById, panels],
  );
  const maxFrames = Math.max(frames[0].length, frames[1].length, 1);

  const summary = useMemo(() => {
    const [left, right] = panels;
    if (!left.result || !right.result) {
      return null;
    }
    return compareSolvers(
      {
        label: solverLabel(left.solver),
        expanded: left.result.nodes_expanded,
        cost: left.result.cost,
      },
      {
        label: solverLabel(right.solver),
        expanded: right.result.nodes_expanded,
        cost: right.result.cost,
      },
    );
  }, [panels]);

  const tourIndices = useMemo(
    () =>
      tspResult
        ? tspResult.route
            .map((node) => indexById.get(node))
            .filter((index): index is number => index !== undefined)
        : [],
    [tspResult, indexById],
  );

  useEffect(() => {
    if (!playing) {
      return;
    }
    let raf = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const elapsed = now - last;
      last = now;
      setStep((current) => {
        const next = current + (speed * elapsed) / 1000;
        if (next >= maxFrames) {
          setPlaying(false);
          return maxFrames;
        }
        return next;
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, speed, maxFrames]);

  const run = useCallback(
    async (
      overrides?: { origin: number; destination: number },
      options?: { animate?: boolean },
    ) => {
      if (!graph) return;
      const origin = overrides?.origin ?? originIndex;
      const destination = overrides?.destination ?? destinationIndex;
      if (origin === null || destination === null || origin === destination) {
        setError("Escolha uma origem e um destino diferentes.");
        return;
      }
      setBusy(true);
      setError(null);
      try {
        const results = await Promise.all(
          panels.map((panel) =>
            runLabPath(IDENTITY, {
              origin: graph.ids[origin],
              destination: graph.ids[destination],
              solver: panel.solver,
              objective,
              trace: true,
              graph: graphName,
              epsilon: panel.epsilon,
            }),
          ),
        );
        setPanels((current) => [
          { ...current[0], result: results[0] },
          { ...current[1], result: results[1] },
        ]);
        const peak = Math.max(
          results[0].expanded_order.length,
          results[1].expanded_order.length,
          1,
        );
        const animate = options?.animate !== false && !prefersReducedMotion;
        setStep(animate ? 0 : peak);
        setPlaying(animate);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : String(cause));
      } finally {
        setBusy(false);
      }
    },
    [graph, graphName, originIndex, destinationIndex, panels, objective, prefersReducedMotion],
  );

  // Poster state: a finished delivery-route race appears as soon as a graph
  // loads, so the page explains itself without a click. Reduced-motion users
  // get that final frame instead of an animation.
  useEffect(() => {
    if (!graph || autoRunRef.current) {
      return;
    }
    autoRunRef.current = true;
    const origin = nearestNodeIndex(
      graph.nodes,
      DEMO_POINTS.restaurant.latitude,
      DEMO_POINTS.restaurant.longitude,
    );
    const destination = nearestNodeIndex(
      graph.nodes,
      DEMO_POINTS.customer.latitude,
      DEMO_POINTS.customer.longitude,
    );
    setOriginIndex(origin);
    setDestinationIndex(destination);
    void run({ origin, destination }, { animate: false });
  }, [graph, run]);

  const pick = (latitude: number, longitude: number) => {
    if (!graph) return;
    const index = nearestNodeIndex(graph.nodes, latitude, longitude);
    if (pickMode === "stops") {
      setStops((current) => (current.length >= 10 ? current : [...current, index]));
      return;
    }
    if (pickMode === "origin") {
      setOriginIndex(index);
      setPickMode("destination");
      return;
    }
    setDestinationIndex(index);
    setPickMode("origin");
  };

  const useDemoRoute = () => {
    if (!graph) return;
    const origin = nearestNodeIndex(
      graph.nodes,
      DEMO_POINTS.restaurant.latitude,
      DEMO_POINTS.restaurant.longitude,
    );
    const destination = nearestNodeIndex(
      graph.nodes,
      DEMO_POINTS.customer.latitude,
      DEMO_POINTS.customer.longitude,
    );
    setOriginIndex(origin);
    setDestinationIndex(destination);
    void run({ origin, destination });
  };

  const pickRandomStops = () => {
    if (!graph) return;
    const count = Math.min(8, graph.node_count);
    const picked: number[] = [];
    const used = new Set<number>();
    // Small deterministic LCG: the same graph always draws the same stops, so
    // a screenshot or a demo run is reproducible.
    let seed = (20261101 + graph.node_count) % 2147483647;
    const nextRandom = () => {
      seed = (seed * 1103515245 + 12345) % 2147483648;
      return seed / 2147483648;
    };
    while (picked.length < count) {
      const index = Math.floor(nextRandom() * graph.node_count);
      if (used.has(index)) continue;
      used.add(index);
      picked.push(index);
    }
    setStops(picked);
    setPickMode("stops");
    setTspResult(null);
    setTspReference(null);
  };

  const runTsp = async () => {
    if (!graph || stops.length < 3) {
      setError("Adicione pelo menos três paradas no mapa (modo “Paradas”).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const nodes = stops.map((index) => graph.ids[index]);
      const primary = await runLabTsp(IDENTITY, {
        nodes,
        solver: tspSolver,
        objective,
        origin_index: 0,
        graph: graphName,
      });
      setTspResult(primary);
      setTspReference(
        tspSolver === "held-karp"
          ? null
          : await runLabTsp(IDENTITY, {
              nodes,
              solver: "held-karp",
              objective,
              origin_index: 0,
              graph: graphName,
            }),
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  const counters = (index: 0 | 1) => {
    const panel = panels[index];
    const framesForPanel = frames[index];
    const shown = Math.min(Math.floor(step), framesForPanel.length);
    const frame = shown > 0 ? framesForPanel[shown - 1] : undefined;
    const finished = panel.result !== null && shown >= framesForPanel.length;
    return (
      <dl className="lab-counters">
        <div>
          <dt>expandidos</dt>
          <dd>{shown}</dd>
        </div>
        <div>
          <dt>fronteira</dt>
          <dd>{frame ? frame.frontier : 0}</dd>
        </div>
        <div>
          <dt>custo parcial</dt>
          <dd>{frame ? formatCost(frame.cost, objective) : "—"}</dd>
        </div>
        <div>
          <dt>resultado</dt>
          <dd>
            {panel.result
              ? finished
                ? `${formatCost(panel.result.cost, objective)} · ${(panel.result.computation_time_ns / 1e6).toFixed(1)} ms`
                : "em andamento"
              : "—"}
          </dd>
        </div>
      </dl>
    );
  };

  return (
    <section className="panel stack">
      <h2>Laboratório de roteirização</h2>
      <p className="muted">
        {graph
          ? `${graph.node_count} nós e ${graph.edge_count} arestas · ${graph.graph_id} ${graph.version}`
          : "Carregando o grafo…"}
        {graph?.attribution ? ` · ${graph.attribution}` : ""}
      </p>
      {error ? (
        <p role="alert" className="error">
          {error}
        </p>
      ) : null}

      <div className="lab-controls">
        <label>
          Grafo{" "}
          <select
            value={graphName}
            onChange={(event) => {
              setGraphName(event.target.value as LabGraphName);
              setStops([]);
              setTspResult(null);
              setTspReference(null);
              setPanels((current) => [
                { ...current[0], result: null },
                { ...current[1], result: null },
              ]);
            }}
          >
            <option value="default">produto (padrão)</option>
            <option value="osm">ruas reais (OSM)</option>
            <option value="synthetic">sintético (77 nós)</option>
          </select>
        </label>
        <label>
          Objetivo{" "}
          <select
            value={objective}
            onChange={(event) => {
              setObjective(event.target.value as "time" | "distance");
              // A result measured on the other objective is not comparable.
              setPanels((current) => [
                { ...current[0], result: null },
                { ...current[1], result: null },
              ]);
              setTspResult(null);
              setTspReference(null);
              setPlaying(false);
              setStep(0);
            }}
          >
            <option value="time">menor tempo</option>
            <option value="distance">menor distância</option>
          </select>
        </label>
        <button type="button" onClick={() => void run()} disabled={busy || !graph}>
          Executar as duas buscas
        </button>
        <button
          type="button"
          className="secondary-button"
          onClick={useDemoRoute}
          disabled={busy || !graph}
        >
          Rota da demo (restaurante → cliente)
        </button>
      </div>

      <div className="lab-controls">
        <span className="muted">Clique no mapa para definir:</span>
        <button
          type="button"
          className={pickMode === "origin" ? "" : "secondary-button"}
          onClick={() => setPickMode("origin")}
        >
          Origem
        </button>
        <button
          type="button"
          className={pickMode === "destination" ? "" : "secondary-button"}
          onClick={() => setPickMode("destination")}
        >
          Destino
        </button>
        <button
          type="button"
          className={pickMode === "stops" ? "" : "secondary-button"}
          onClick={() => setPickMode("stops")}
        >
          Paradas ({stops.length})
        </button>
        <button type="button" className="secondary-button" onClick={() => setStops([])}>
          Limpar paradas
        </button>
      </div>

      <div className="lab-controls">
        <button
          type="button"
          onClick={() => setPlaying((value) => !value)}
          disabled={maxFrames <= 1}
        >
          {playing ? "Pausar" : "Animar"}
        </button>
        <button
          type="button"
          className="secondary-button"
          onClick={() => {
            setPlaying(false);
            setStep(0);
          }}
        >
          Reiniciar
        </button>
        <button type="button" className="secondary-button" onClick={() => setStep(maxFrames)}>
          Mostrar fim
        </button>
        <label>
          Velocidade{" "}
          <input
            type="range"
            min={30}
            max={4000}
            step={30}
            value={speed}
            onChange={(event) => setSpeed(Number(event.target.value))}
            aria-label="Nós expandidos por segundo"
          />
        </label>
        <span className="muted">{speed} nós/s</span>
        <span className="muted">
          {Math.min(Math.floor(step), maxFrames)} / {maxFrames} expansões
        </span>
      </div>

      <div className="lab-panels">
        {([0, 1] as const).map((index) => (
          <div className="panel" key={index}>
            <label>
              Solver{" "}
              <select
                value={panels[index].solver}
                onChange={(event) => {
                  const solver = event.target.value as LabSolverName;
                  // Never let the label and the drawn result disagree.
                  setPanels((current) => {
                    const next = [...current] as [PanelState, PanelState];
                    next[index] = { ...next[index], solver, result: null };
                    return next;
                  });
                  setPlaying(false);
                  setStep(0);
                }}
              >
                {SOLVERS.map((solver) => (
                  <option key={solver.value} value={solver.value}>
                    {solver.label}
                  </option>
                ))}
              </select>
            </label>
            {panels[index].solver === "weighted-astar" ? (
              <label>
                ε{" "}
                <input
                  type="number"
                  min={1}
                  max={10}
                  step={0.5}
                  value={panels[index].epsilon}
                  onChange={(event) => {
                    const epsilon = Number(event.target.value);
                    setPanels((current) => {
                      const next = [...current] as [PanelState, PanelState];
                      next[index] = { ...next[index], epsilon, result: null };
                      return next;
                    });
                    setPlaying(false);
                    setStep(0);
                  }}
                />
              </label>
            ) : null}
            <p className="muted">
              {SOLVERS.find((solver) => solver.value === panels[index].solver)?.hint}
              {panels[index].result?.preprocessing_time_ns
                ? ` · pré-processamento ${(panels[index].result.preprocessing_time_ns / 1e6).toFixed(0)} ms`
                : ""}
            </p>
            {graph && bounds ? (
              <LabCanvas
                graph={graph}
                bounds={bounds}
                frames={frames[index]}
                step={step}
                path={pathIndices(indexById, panels[index].result?.node_path ?? [])}
                originIndex={originIndex}
                destinationIndex={destinationIndex}
                onPick={pick}
                overlay={index === 0 ? tourIndices : undefined}
                label={`${solverLabel(panels[index].solver)}: ${frames[index].length} nós expandidos, ${panels[index].result?.node_path.length ?? 0} nós no caminho`}
              />
            ) : null}
            {counters(index)}
          </div>
        ))}
      </div>

      {summary ? (
        <p className="lab-summary" role="status">
          <strong>{summary.fewer}</strong> expandiu {summary.ratio.toFixed(1)}× menos nós que{" "}
          <strong>{summary.more}</strong> —{" "}
          {summary.sameCost
            ? `mesmo custo (${formatCost(summary.fewerCost, objective)})`
            : `custo ${formatCost(summary.fewerCost, objective)} vs ${formatCost(summary.moreCost, objective)}`}
          .
        </p>
      ) : null}

      <div className="panel stack">
        <h3>Multi-parada (TSP)</h3>
        <p className="muted">
          Use o modo “Paradas” para marcar até 10 pontos no mapa e compare o solver escolhido com
          o ótimo exato (Held-Karp) na mesma matriz de custos.
        </p>
        <div className="lab-controls">
          <label>
            Solver{" "}
            <select
              value={tspSolver}
              onChange={(event) =>
                setTspSolver(event.target.value as "held-karp" | "two-opt" | "nearest-neighbor")
              }
            >
              <option value="nearest-neighbor">vizinho mais próximo</option>
              <option value="two-opt">2-opt</option>
              <option value="held-karp">Held-Karp (exato)</option>
            </select>
          </label>
          <button type="button" onClick={() => void runTsp()} disabled={busy || !graph}>
            Resolver paradas
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={pickRandomStops}
            disabled={busy || !graph}
          >
            8 paradas aleatórias
          </button>
        </div>
        {tspResult ? (
          <p>
            {tspResult.solver_name}: {formatCost(tspResult.total_cost, objective)} ·{" "}
            {tspResult.routes_evaluated} avaliações ·{" "}
            {(tspResult.execution_time_ns / 1e6).toFixed(2)} ms
            {tspReference ? (
              <>
                {" "}
                · Held-Karp: {formatCost(tspReference.total_cost, objective)} ·{" "}
                {gapLabel(tspResult.total_cost, tspReference.total_cost)}
              </>
            ) : null}
          </p>
        ) : null}
        {tspResult ? <p className="muted">{tspResult.route.join(" → ")}</p> : null}
        {tspResult ? (
          <p className="muted">
            ordem das paradas desenhada no painel esquerdo em linhas retas; o custo acima usa as
            ruas reais.
          </p>
        ) : null}
      </div>

      {traffic ? (
        <div className="panel stack">
          <h3>ETA ao longo do dia</h3>
          <p className="muted">
            mesma origem e destino, perfil <strong>{traffic.profile_id}</strong> · pico às{" "}
            {traffic.peak_hour}h: {formatDuration(traffic.peak_seconds)} · madrugada às{" "}
            {traffic.night_hour}h: {formatDuration(traffic.night_seconds)} · sem trânsito:{" "}
            {formatDuration(traffic.static_seconds)}
          </p>
          <div
            className="traffic-strip"
            role="img"
            aria-label={`ETA por hora do dia: pico às ${traffic.peak_hour} horas com ${formatDuration(traffic.peak_seconds)}`}
          >
            {traffic.points.map((point) => {
              const ceiling = Math.max(...traffic.points.map((item) => item.estimated_seconds));
              const height = Math.max(8, (point.estimated_seconds / ceiling) * 100);
              const className =
                point.hour === traffic.peak_hour
                  ? "peak"
                  : point.hour === traffic.night_hour
                    ? "night"
                    : undefined;
              return (
                <span
                  key={point.hour}
                  className={className}
                  style={{ height: `${height}%` }}
                  title={`${point.hour}h · ${formatDuration(point.estimated_seconds)}`}
                />
              );
            })}
          </div>
          <div className="traffic-strip-labels">
            <span>0h</span>
            <span>6h</span>
            <span>12h</span>
            <span>18h</span>
            <span>23h</span>
          </div>
          <p className="muted">{traffic.profile_source}</p>
        </div>
      ) : null}

      {benchmarkRows.length ? (
        <div className="panel stack">
          <h3>Benchmarks publicados</h3>
          <table>
            <caption className="muted">
              paradas · custo e tempo por solver (docs/benchmarks/routing.json)
            </caption>
            <thead>
              <tr>
                <th scope="col">paradas</th>
                <th scope="col">Held-Karp</th>
                <th scope="col">2-opt</th>
                <th scope="col">vizinho</th>
                <th scope="col">força bruta</th>
              </tr>
            </thead>
            <tbody>
              {benchmarkRows.map((row, index) => (
                <tr key={index}>
                  <th scope="row">{String(row.stops ?? index)}</th>
                  {(["held_karp", "two_opt", "nearest_neighbor", "brute_force"] as const).map(
                    (solver) => (
                      <td key={solver}>{benchmarkCell(row[solver], objective)}</td>
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

function formatCost(value: number, objective: string): string {
  return objective === "time" ? formatDuration(value) : `${(value / 1000).toFixed(2)} km`;
}

function gapLabel(value: number, reference: number): string {
  if (reference <= 0) {
    return "—";
  }
  const gap = ((value - reference) / reference) * 100;
  return gap <= 0.001 ? "ótimo" : `${gap.toFixed(1)}% acima do ótimo`;
}

function benchmarkCell(entry: unknown, objective: string): string {
  if (!entry || typeof entry !== "object") {
    return "—";
  }
  const record = entry as { total_cost?: number; solver_time_ns?: number };
  const cost =
    typeof record.total_cost === "number" ? formatCost(record.total_cost, objective) : "—";
  const time =
    typeof record.solver_time_ns === "number"
      ? `${(record.solver_time_ns / 1e6).toFixed(1)} ms`
      : "";
  return time ? `${cost} (${time})` : cost;
}
