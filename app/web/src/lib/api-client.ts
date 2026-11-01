import type {
  Address,
  Cart,
  CheckoutResult,
  CourierProfile,
  DemoSnapshot,
  Delivery,
  DomainEvent,
  MenuItem,
  Metrics,
  Notification,
  Order,
  OrderSummary,
  RestaurantSummary,
  RoutePlan,
  TrackingView,
} from "./api-types";
import type { DemoIdentity } from "./identities";

export type HealthResponse = {
  status: string;
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    public readonly detail: string,
    public readonly fieldErrors: Record<string, string>,
  ) {
    super(detail);
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  identity?: DemoIdentity;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { identity, ...init } = options;
  const response = await fetch(path, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(identity ? { "x-demo-identity": identity } : {}),
      ...init.headers,
    },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });

  if (!response.ok) {
    let code = "unknown_error";
    let detail = `A chamada à API falhou com status ${response.status}.`;
    let fieldErrors: Record<string, string> = {};
    try {
      const envelope = (await response.json()) as {
        code?: string;
        detail?: string;
        field_errors?: Record<string, string>;
      };
      code = envelope.code ?? code;
      detail = envelope.detail ?? detail;
      fieldErrors = envelope.field_errors ?? {};
    } catch {
      // non-JSON error body — keep defaults
    }
    throw new ApiError(response.status, code, detail, fieldErrors);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/v1/health");
}

// --- catalog ---

export function listRestaurants(): Promise<{ restaurants: RestaurantSummary[] }> {
  return request("/api/v1/restaurants");
}

export function getRestaurant(restaurantId: string): Promise<RestaurantSummary> {
  return request(`/api/v1/restaurants/${restaurantId}`);
}

export function getMenu(restaurantId: string): Promise<{ items: MenuItem[] }> {
  return request(`/api/v1/restaurants/${restaurantId}/menu`);
}

// --- customer ---

export function getCart(identity: DemoIdentity): Promise<Cart> {
  return request("/api/v1/me/cart", { identity });
}

export function addCartItem(
  identity: DemoIdentity,
  menuItemId: string,
  quantity: number,
  observation = "",
): Promise<Cart> {
  return request("/api/v1/me/cart/items", {
    method: "POST",
    identity,
    body: { menu_item_id: menuItemId, quantity, observation },
  });
}

export function updateCartItem(
  identity: DemoIdentity,
  lineId: string,
  patch: { quantity?: number; observation?: string },
): Promise<Cart> {
  return request(`/api/v1/me/cart/items/${lineId}`, {
    method: "PATCH",
    identity,
    body: patch,
  });
}

export function removeCartItem(identity: DemoIdentity, lineId: string): Promise<void> {
  return request(`/api/v1/me/cart/items/${lineId}`, { method: "DELETE", identity });
}

export function applyCoupon(identity: DemoIdentity, code: string): Promise<Cart> {
  return request("/api/v1/me/cart/coupon", { method: "POST", identity, body: { code } });
}

export function removeCoupon(identity: DemoIdentity): Promise<void> {
  return request("/api/v1/me/cart/coupon", { method: "DELETE", identity });
}

export function listAddresses(identity: DemoIdentity): Promise<{ addresses: Address[] }> {
  return request("/api/v1/me/addresses", { identity });
}

export function listMyOrders(identity: DemoIdentity): Promise<{ orders: OrderSummary[] }> {
  return request("/api/v1/me/orders", { identity });
}

export function checkout(
  identity: DemoIdentity,
  body: { address_id: string; payment_method: string; simulate_outcome?: string },
): Promise<CheckoutResult> {
  return request("/api/v1/me/orders/checkout", {
    method: "POST",
    identity,
    body,
    headers: { "idempotency-key": `web-${crypto.randomUUID()}` },
  });
}

// --- orders (shared reads) ---

export function getOrder(identity: DemoIdentity, orderId: string): Promise<Order> {
  return request(`/api/v1/orders/${orderId}`, { identity });
}

export function getTracking(identity: DemoIdentity, orderId: string): Promise<TrackingView> {
  return request(`/api/v1/orders/${orderId}/tracking`, { identity });
}

export function listOrderNotifications(
  identity: DemoIdentity,
  orderId: string,
): Promise<{ notifications: Notification[] }> {
  return request(`/api/v1/orders/${orderId}/notifications`, { identity });
}

// --- restaurant ---

export function listRestaurantQueue(
  identity: DemoIdentity,
): Promise<{ orders: OrderSummary[] }> {
  return request("/api/v1/restaurant/orders", { identity });
}

export function restaurantCommand(
  identity: DemoIdentity,
  orderId: string,
  action: "confirm" | "prepare" | "ready",
): Promise<{ order_id: string; state: string; version: number }> {
  return request(`/api/v1/restaurant/orders/${orderId}/${action}`, {
    method: "POST",
    identity,
  });
}

// --- courier ---

export function setCourierAvailability(
  identity: DemoIdentity,
  available: boolean,
): Promise<{ courier_id: string; status: string; version: number }> {
  return request("/api/v1/courier/availability", {
    method: "PUT",
    identity,
    body: { available },
  });
}

export function listDeliveryOffers(identity: DemoIdentity): Promise<{ deliveries: (Delivery | null)[] }> {
  return request("/api/v1/courier/deliveries/offers", { identity });
}

export function getActiveDelivery(identity: DemoIdentity): Promise<{
  deliveries: Delivery[];
  batch: { id: string; status: string; delivery_ids: string[] } | null;
  route: RoutePlan | null;
}> {
  return request("/api/v1/courier/deliveries/active", { identity });
}

export function acceptBatch(
  identity: DemoIdentity,
  deliveryIds: string[],
): Promise<{ batch: { id: string; status: string } }> {
  return request("/api/v1/courier/batches/accept", {
    method: "POST",
    identity,
    body: { delivery_ids: deliveryIds },
  });
}

export function courierCommand(
  identity: DemoIdentity,
  deliveryId: string,
  action: "accept" | "pickup" | "start" | "complete",
): Promise<{ delivery: Delivery }> {
  return request(`/api/v1/courier/deliveries/${deliveryId}/${action}`, {
    method: "POST",
    identity,
  });
}

export function advanceRouteLocation(
  identity: DemoIdentity,
  deliveryId: string,
): Promise<{ events: { delivery_id: string; sequence: number; latitude: number; longitude: number }[] }> {
  return request(`/api/v1/courier/deliveries/${deliveryId}/route-advance`, {
    method: "POST",
    identity,
  });
}

export function postCourierLocation(
  identity: DemoIdentity,
  deliveryId: string,
  sequence: number,
  latitude: number,
  longitude: number,
): Promise<unknown> {
  return request(`/api/v1/courier/deliveries/${deliveryId}/location`, {
    method: "POST",
    identity,
    body: { sequence, latitude, longitude },
  });
}

// --- operations ---

export function listOperationsOrders(identity: DemoIdentity): Promise<{ orders: OrderSummary[] }> {
  return request("/api/v1/operations/orders", { identity });
}

export function listOperationsEvents(
  identity: DemoIdentity,
  since = 0,
): Promise<{ events: DomainEvent[] }> {
  return request(`/api/v1/operations/events?since=${since}`, { identity });
}

export function listOperationsCouriers(
  identity: DemoIdentity,
): Promise<{ couriers: CourierProfile[] }> {
  return request("/api/v1/operations/couriers", { identity });
}

export function getOperationsMetrics(identity: DemoIdentity): Promise<Metrics> {
  return request("/api/v1/operations/metrics", { identity });
}

// --- demo scenario ---

export function getDemoScenario(): Promise<DemoSnapshot> {
  return request("/api/v1/demo/scenario");
}

export function resetDemo(): Promise<DemoSnapshot> {
  return request("/api/v1/demo/reset", { method: "POST" });
}

export function advanceDemo(eventCount: number): Promise<DemoSnapshot> {
  return request("/api/v1/demo/advance", {
    method: "POST",
    body: { event_count: eventCount },
  });
}

export function advanceDemoClock(minutes: number): Promise<DemoSnapshot> {
  return request("/api/v1/demo/clock", {
    method: "POST",
    body: { minutes },
  });
}

// --- algorithm lab ---

export type LabGraphName = "default" | "osm" | "synthetic";

export type LabGraph = {
  graph_id: string;
  version: string;
  source: string;
  attribution: string;
  max_speed_mps: number;
  node_count: number;
  edge_count: number;
  /** Node ids, aligned with `nodes` and `edges` indices. */
  ids: string[];
  /** `[latitude, longitude]` per node. */
  nodes: [number, number][];
  /** `[fromIndex, toIndex, speedKmh]` per directed edge. */
  edges: [number, number, number][];
};

export type LabSolverName =
  | "astar"
  | "dijkstra"
  | "alt"
  | "bidirectional"
  | "ch"
  | "td-astar"
  | "td-dijkstra"
  | "weighted-astar";

export type LabPathResult = {
  node_path: string[];
  expanded_order: string[];
  frontier_sizes: number[];
  expansion_costs: number[];
  distance_meters: number;
  estimated_seconds: number;
  cost: number;
  solver_name: string;
  solver_version: string;
  nodes_expanded: number;
  computation_time_ns: number;
  preprocessing_time_ns: number;
  objective: string;
  geometry: [number, number][];
};

export type LabTspResult = {
  route: string[];
  total_cost: number;
  solver_name: string;
  execution_time_ns: number;
  routes_evaluated: number;
  objective: string;
};

export type LabBenchmarks = {
  generated_at?: string;
  /** TSP ladder over cost matrices built from the committed street graph. */
  tsp_graph?: Record<string, unknown>[];
  /** TSP ladder over seeded random matrices. */
  tsp_random?: Record<string, unknown>[];
  path?: Record<string, unknown>;
};

export function getLabGraph(
  identity: DemoIdentity,
  graph: LabGraphName = "default",
): Promise<LabGraph> {
  return request<LabGraph>(`/api/v1/lab/graph?graph=${graph}`, { identity });
}

export function runLabPath(
  identity: DemoIdentity,
  body: {
    origin: string;
    destination: string;
    solver: LabSolverName;
    objective: "time" | "distance";
    trace: boolean;
    graph?: LabGraphName;
    epsilon?: number;
    landmarks?: number;
    departure_hour?: number;
  },
): Promise<LabPathResult> {
  return request<LabPathResult>("/api/v1/lab/path", {
    method: "POST",
    identity,
    body,
  });
}

export function runLabTsp(
  identity: DemoIdentity,
  body: {
    nodes: string[];
    solver: "held-karp" | "nearest-neighbor" | "two-opt";
    objective: "time" | "distance";
    origin_index: number;
    graph?: LabGraphName;
  },
): Promise<LabTspResult> {
  return request<LabTspResult>("/api/v1/lab/tsp", {
    method: "POST",
    identity,
    body,
  });
}

export function getLabBenchmarks(identity: DemoIdentity): Promise<LabBenchmarks> {
  return request<LabBenchmarks>("/api/v1/lab/benchmarks", { identity });
}

export type LabTrafficPoint = {
  hour: number;
  estimated_seconds: number;
  distance_meters: number;
};

export type LabTraffic = {
  profile_id: string;
  profile_source: string;
  static_seconds: number;
  points: LabTrafficPoint[];
  peak_hour: number;
  peak_seconds: number;
  night_hour: number;
  night_seconds: number;
};

export function getLabTraffic(
  identity: DemoIdentity,
  origin: string,
  destination: string,
  graph: LabGraphName = "default",
): Promise<LabTraffic> {
  const params = new URLSearchParams({ origin, destination, graph });
  return request<LabTraffic>(`/api/v1/lab/traffic?${params.toString()}`, { identity });
}

export function rateOrder(
  identity: DemoIdentity,
  orderId: string,
  stars: number,
): Promise<{ order: { id: string; state: string } }> {
  return request(`/api/v1/me/orders/${orderId}/rate`, {
    method: "POST",
    identity,
    body: { stars },
  });
}

export function cancelOrder(
  identity: DemoIdentity,
  orderId: string,
): Promise<{ order: { id: string; state: string } }> {
  return request(`/api/v1/me/orders/${orderId}/cancel`, {
    method: "POST",
    identity,
  });
}

export type OrderTimeline = {
  order_id: string;
  state: string;
  stages: { stage: string; occurred_at: string; duration_seconds: number }[];
  eta_estimated_seconds: number | null;
  eta_actual_seconds: number | null;
  eta_error_seconds: number | null;
};

export function listOperationsTimeline(
  identity: DemoIdentity,
): Promise<{ orders: OrderTimeline[] }> {
  return request("/api/v1/operations/timeline", { identity });
}
