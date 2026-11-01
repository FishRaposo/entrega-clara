import {
  buildFrames,
  compareSolvers,
  nearestNodeIndex,
  pathIndices,
  approximateMeters,
} from "../../app/web/src/lib/lab-trace";
import { boundsOf, createProjection } from "../../app/web/src/lib/projection";

test("projection round-trips a coordinate through canvas space", () => {
  const bounds = boundsOf([
    { latitude: -23.55, longitude: -46.64 },
    { latitude: -23.54, longitude: -46.63 },
  ]);
  const projection = createProjection(bounds, { width: 400, height: 300 });
  const [x, y] = projection.project(-23.545, -46.635);
  const back = projection.invert(x, y);
  expect(back.latitude).toBeCloseTo(-23.545, 6);
  expect(back.longitude).toBeCloseTo(-46.635, 6);
});

test("projection keeps a single point inside the viewport", () => {
  const bounds = boundsOf([{ latitude: -23.55, longitude: -46.64 }]);
  const projection = createProjection(bounds, { width: 200, height: 200 });
  const [x, y] = projection.project(-23.55, -46.64);
  expect(x).toBeCloseTo(100, 3);
  expect(y).toBeCloseTo(100, 3);
});

test("invert clamps to the projected bounds", () => {
  const bounds = boundsOf([
    { latitude: -23.55, longitude: -46.64 },
    { latitude: -23.54, longitude: -46.63 },
  ]);
  const projection = createProjection(bounds, { width: 100, height: 100 });
  const outside = projection.invert(1_000, -1_000);
  expect(outside.latitude).toBeLessThanOrEqual(projection.bounds.maxLatitude);
  expect(outside.latitude).toBeGreaterThanOrEqual(projection.bounds.minLatitude);
  expect(outside.longitude).toBeLessThanOrEqual(projection.bounds.maxLongitude);
});

test("nearest node index picks the closest street corner", () => {
  const nodes: [number, number][] = [
    [-23.55, -46.64],
    [-23.54, -46.63],
    [-23.545, -46.635],
  ];
  expect(nearestNodeIndex(nodes, -23.5451, -46.6351)).toBe(2);
  expect(nearestNodeIndex(nodes, -23.5401, -46.6301)).toBe(1);
});

test("approximate meters is plausible at São Paulo latitudes", () => {
  const meters = approximateMeters(-23.55, -46.64, -23.55, -46.639);
  // 0.001° of longitude near -23.55° is roughly 102 m.
  expect(meters).toBeGreaterThan(95);
  expect(meters).toBeLessThan(110);
});

test("frames zip the solver trace and skip unknown nodes", () => {
  const index = new Map([
    ["a", 0],
    ["b", 1],
  ]);
  const frames = buildFrames(index, ["a", "ghost", "b"], [5, 4, 3], [0, 1.5, 2.5]);
  expect(frames).toEqual([
    { nodeIndex: 0, frontier: 5, cost: 0 },
    { nodeIndex: 1, frontier: 3, cost: 2.5 },
  ]);
});

test("frames tolerate a trace without series", () => {
  const frames = buildFrames(new Map([["a", 7]]), ["a"]);
  expect(frames).toEqual([{ nodeIndex: 7, frontier: 0, cost: 0 }]);
});

test("path indices keep only known nodes and preserve order", () => {
  const index = new Map([
    ["a", 3],
    ["b", 9],
  ]);
  expect(pathIndices(index, ["a", "missing", "b"])).toEqual([3, 9]);
});

test("compareSolvers reports the solver that expanded fewer nodes", () => {
  const comparison = compareSolvers(
    { label: "Dijkstra", expanded: 167, cost: 668 },
    { label: "A* + ALT", expanded: 70, cost: 668 },
  );
  expect(comparison).not.toBeNull();
  expect(comparison?.fewer).toBe("A* + ALT");
  expect(comparison?.more).toBe("Dijkstra");
  expect(comparison?.ratio).toBeCloseTo(167 / 70, 5);
  expect(comparison?.sameCost).toBe(true);
  expect(comparison?.costDeltaPercent).toBeCloseTo(0, 5);
});

test("compareSolvers keeps the side order when the left panel wins", () => {
  const comparison = compareSolvers(
    { label: "A*", expanded: 40, cost: 100 },
    { label: "Dijkstra", expanded: 120, cost: 104 },
  );
  expect(comparison?.fewer).toBe("A*");
  expect(comparison?.ratio).toBeCloseTo(3, 5);
  expect(comparison?.sameCost).toBe(false);
  expect(comparison?.costDeltaPercent).toBeCloseTo(4, 5);
  expect(comparison?.fewerCost).toBe(100);
  expect(comparison?.moreCost).toBe(104);
});

test("compareSolvers treats a tie as ratio one", () => {
  const comparison = compareSolvers(
    { label: "A", expanded: 12, cost: 50 },
    { label: "B", expanded: 12, cost: 50 },
  );
  expect(comparison?.ratio).toBe(1);
  expect(comparison?.sameCost).toBe(true);
});

test("compareSolvers says nothing when neither search ran", () => {
  expect(
    compareSolvers(
      { label: "A", expanded: 0, cost: 0 },
      { label: "B", expanded: 0, cost: 0 },
    ),
  ).toBeNull();
});
