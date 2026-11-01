"use client";

import { useEffect, useMemo, useRef } from "react";
import type { LabGraph } from "../lib/api-client";
import type { TraceFrame } from "../lib/lab-trace";
import { createProjection, type GeoBounds } from "../lib/projection";

const WIDTH = 560;
const HEIGHT = 400;

type LabCanvasProps = {
  graph: LabGraph;
  bounds: GeoBounds;
  frames: TraceFrame[];
  step: number;
  path: number[];
  /** Optional dashed polyline (e.g. a TSP stop order drawn as straight legs). */
  overlay?: number[];
  originIndex: number | null;
  destinationIndex: number | null;
  onPick?: (latitude: number, longitude: number) => void;
  label: string;
};

function layer(width: number, height: number, dpr: number): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  const context = canvas.getContext("2d");
  context?.scale(dpr, dpr);
  return canvas;
}

/**
 * Canvas street graph with a search that can be replayed frame by frame.
 *
 * Two cached layers keep a 15k-node graph animatable: a static base (edges and
 * junctions) drawn once per graph, and a progress layer that only receives the
 * newly expanded nodes. Replaying backwards rebuilds the progress layer; the
 * visible canvas is always base + progress + overlays.
 */
export function LabCanvas({
  graph,
  bounds,
  frames,
  step,
  path,
  overlay,
  originIndex,
  destinationIndex,
  onPick,
  label,
}: LabCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const baseRef = useRef<HTMLCanvasElement | null>(null);
  const progressRef = useRef<HTMLCanvasElement | null>(null);
  const drawnRef = useRef(0);

  const dpr = useMemo(
    () => (typeof window === "undefined" ? 1 : window.devicePixelRatio || 1),
    [],
  );
  const projection = useMemo(
    () => createProjection(bounds, { width: WIDTH, height: HEIGHT }),
    [bounds],
  );
  const degrees = useMemo(() => {
    const counts = new Uint16Array(graph.nodes.length);
    for (const [from, to] of graph.edges) {
      counts[from] += 1;
      counts[to] += 1;
    }
    return counts;
  }, [graph]);

  useEffect(() => {
    const base = layer(WIDTH, HEIGHT, dpr);
    const context = base.getContext("2d");
    if (!context) {
      return;
    }
    context.fillStyle = "#0b1220";
    context.fillRect(0, 0, WIDTH, HEIGHT);

    const slow = new Path2D();
    const fast = new Path2D();
    for (const [from, to, speed] of graph.edges) {
      const [ax, ay] = projection.project(graph.nodes[from][0], graph.nodes[from][1]);
      const [bx, by] = projection.project(graph.nodes[to][0], graph.nodes[to][1]);
      const target = speed >= 45 ? fast : slow;
      target.moveTo(ax, ay);
      target.lineTo(bx, by);
    }
    context.lineWidth = 0.7;
    context.strokeStyle = "#1e293b";
    context.stroke(slow);
    context.strokeStyle = "#243d5c";
    context.stroke(fast);

    context.fillStyle = "#334155";
    for (let index = 0; index < graph.nodes.length; index += 1) {
      if (degrees[index] < 3) {
        continue;
      }
      const [x, y] = projection.project(graph.nodes[index][0], graph.nodes[index][1]);
      context.fillRect(x - 0.6, y - 0.6, 1.2, 1.2);
    }

    baseRef.current = base;
    progressRef.current = layer(WIDTH, HEIGHT, dpr);
    drawnRef.current = 0;
  }, [graph, projection, degrees, dpr]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const base = baseRef.current;
    let progress = progressRef.current;
    if (!canvas || !base) {
      return;
    }
    if (!progress) {
      progress = layer(WIDTH, HEIGHT, dpr);
      progressRef.current = progress;
    }
    const progressContext = progress.getContext("2d");
    if (!progressContext) {
      return;
    }
    const shown = Math.min(Math.floor(step), frames.length);
    if (shown < drawnRef.current) {
      progressContext.clearRect(0, 0, WIDTH, HEIGHT);
      drawnRef.current = 0;
    }
    if (shown > drawnRef.current) {
      progressContext.fillStyle = "#f59e0b";
      for (let index = drawnRef.current; index < shown; index += 1) {
        const [x, y] = projection.project(
          graph.nodes[frames[index].nodeIndex][0],
          graph.nodes[frames[index].nodeIndex][1],
        );
        progressContext.beginPath();
        progressContext.arc(x, y, 2.4, 0, Math.PI * 2);
        progressContext.fill();
      }
      drawnRef.current = shown;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    context.clearRect(0, 0, WIDTH, HEIGHT);
    context.drawImage(base, 0, 0, WIDTH, HEIGHT);
    context.drawImage(progress, 0, 0, WIDTH, HEIGHT);

    if (path.length > 1) {
      context.beginPath();
      path.forEach((nodeIndex, position) => {
        const [x, y] = projection.project(
          graph.nodes[nodeIndex][0],
          graph.nodes[nodeIndex][1],
        );
        if (position === 0) {
          context.moveTo(x, y);
        } else {
          context.lineTo(x, y);
        }
      });
      context.strokeStyle = shown >= frames.length ? "#22c55e" : "#1d4ed8";
      context.lineWidth = 2.6;
      context.stroke();
    }

    if (overlay && overlay.length > 1) {
      context.save();
      context.setLineDash([5, 4]);
      context.beginPath();
      overlay.forEach((nodeIndex, position) => {
        const [x, y] = projection.project(
          graph.nodes[nodeIndex][0],
          graph.nodes[nodeIndex][1],
        );
        if (position === 0) {
          context.moveTo(x, y);
        } else {
          context.lineTo(x, y);
        }
      });
      context.strokeStyle = "#a855f7";
      context.lineWidth = 1.6;
      context.stroke();
      context.restore();
    }

    const marker = (nodeIndex: number, fill: string) => {
      const [x, y] = projection.project(
        graph.nodes[nodeIndex][0],
        graph.nodes[nodeIndex][1],
      );
      context.beginPath();
      context.arc(x, y, 7, 0, Math.PI * 2);
      context.fillStyle = fill;
      context.fill();
      context.lineWidth = 2;
      context.strokeStyle = "#e2e8f0";
      context.stroke();
    };
    if (originIndex !== null) {
      marker(originIndex, "#2563eb");
    }
    if (destinationIndex !== null) {
      marker(destinationIndex, "#a855f7");
    }
    if (shown >= 1 && shown < frames.length) {
      const [x, y] = projection.project(
        graph.nodes[frames[shown - 1].nodeIndex][0],
        graph.nodes[frames[shown - 1].nodeIndex][1],
      );
      context.beginPath();
      context.arc(x, y, 5, 0, Math.PI * 2);
      context.strokeStyle = "#fbbf24";
      context.lineWidth = 1.5;
      context.stroke();
    }
  }, [step, frames, path, overlay, originIndex, destinationIndex, graph, projection, dpr]);

  return (
    <canvas
      ref={canvasRef}
      width={Math.round(WIDTH * dpr)}
      height={Math.round(HEIGHT * dpr)}
      style={{ width: "100%", maxWidth: `${WIDTH}px`, height: "auto" }}
      className="lab-canvas"
      role="img"
      aria-label={label}
      onClick={(event) => {
        if (!onPick) {
          return;
        }
        const rect = event.currentTarget.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width) * WIDTH;
        const y = ((event.clientY - rect.top) / rect.height) * HEIGHT;
        const point = projection.invert(x, y);
        onPick(point.latitude, point.longitude);
      }}
    />
  );
}
