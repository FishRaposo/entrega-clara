/** Pure helpers behind the animated lab: trace framing and coordinate lookups. */

export type TraceFrame = {
  /** Index of the expanded node in the graph's node array. */
  nodeIndex: number;
  /** Priority-queue size after this expansion (an upper bound, lazy deletion). */
  frontier: number;
  /** Settled cost of the expanded node under the active objective. */
  cost: number;
};

const EARTH_RADIUS_M = 6_371_000;

/** Equirectangular meters — accurate enough to pick a street corner. */
export function approximateMeters(
  latitude: number,
  longitude: number,
  otherLatitude: number,
  otherLongitude: number,
): number {
  const meanLatitude = ((latitude + otherLatitude) / 2) * (Math.PI / 180);
  const dLat = (latitude - otherLatitude) * (Math.PI / 180);
  const dLon = (longitude - otherLongitude) * (Math.PI / 180) * Math.cos(meanLatitude);
  return EARTH_RADIUS_M * Math.sqrt(dLat * dLat + dLon * dLon);
}

export function nearestNodeIndex(
  nodes: [number, number][],
  latitude: number,
  longitude: number,
): number {
  let bestIndex = 0;
  let bestDistance = Infinity;
  for (let index = 0; index < nodes.length; index += 1) {
    const [nodeLatitude, nodeLongitude] = nodes[index];
    const distance = approximateMeters(latitude, longitude, nodeLatitude, nodeLongitude);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = index;
    }
  }
  return bestIndex;
}

/**
 * Zip the solver's parallel trace arrays into frames, dropping ids the payload
 * does not know (defensive: the UI must not crash on an unexpected node).
 */
export function buildFrames(
  nodeIndexById: Map<string, number>,
  expandedOrder: string[],
  frontierSizes: number[] = [],
  expansionCosts: number[] = [],
): TraceFrame[] {
  const frames: TraceFrame[] = [];
  for (let index = 0; index < expandedOrder.length; index += 1) {
    const nodeIndex = nodeIndexById.get(expandedOrder[index]);
    if (nodeIndex === undefined) {
      continue;
    }
    frames.push({
      nodeIndex,
      frontier: frontierSizes[index] ?? 0,
      cost: expansionCosts[index] ?? 0,
    });
  }
  return frames;
}

export function pathIndices(nodeIndexById: Map<string, number>, nodePath: string[]): number[] {
  const indices: number[] = [];
  for (const node of nodePath) {
    const index = nodeIndexById.get(node);
    if (index !== undefined) {
      indices.push(index);
    }
  }
  return indices;
}

export type SolverRun = {
  label: string;
  expanded: number;
  cost: number;
};

export type SolverComparison = {
  /** Label of the solver that expanded fewer nodes. */
  fewer: string;
  /** Label of the solver that expanded more nodes. */
  more: string;
  /** expansions(more) / expansions(fewer), never below 1. */
  ratio: number;
  /** Cost of the cheaper-of-the-two by expansions, and of the other one. */
  fewerCost: number;
  moreCost: number;
  /** True when both solvers reached the same cost within the tolerance. */
  sameCost: boolean;
  /** Percentage difference of the more expensive result against the cheaper one. */
  costDeltaPercent: number;
};

/**
 * Summarise a two-solver race for the lab caption. Returns ``null`` when there
 * is nothing honest to say (no expansions recorded on either side).
 */
export function compareSolvers(
  left: SolverRun,
  right: SolverRun,
  tolerancePercent = 0.05,
): SolverComparison | null {
  if (left.expanded <= 0 && right.expanded <= 0) {
    return null;
  }
  const leftFewer = left.expanded <= right.expanded;
  const fewerRun = leftFewer ? left : right;
  const moreRun = leftFewer ? right : left;
  const ratio =
    fewerRun.expanded > 0 ? Math.max(1, moreRun.expanded / fewerRun.expanded) : 1;
  const cheapest = Math.min(left.cost, right.cost);
  const costDeltaPercent =
    cheapest > 0 ? ((Math.max(left.cost, right.cost) - cheapest) / cheapest) * 100 : 0;
  return {
    fewer: fewerRun.label,
    more: moreRun.label,
    ratio,
    fewerCost: fewerRun.cost,
    moreCost: moreRun.cost,
    sameCost: costDeltaPercent <= tolerancePercent,
    costDeltaPercent,
  };
}
