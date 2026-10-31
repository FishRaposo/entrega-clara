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

export function getActiveDelivery(identity: DemoIdentity): Promise<{ delivery: Delivery | null }> {
  return request("/api/v1/courier/deliveries/active", { identity });
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

export type LabGraph = {
  graph_id: string;
  version: string;
  max_speed_mps: number;
  nodes: { id: string; latitude: number; longitude: number }[];
  edges: { from: string; to: string; speed_kmh: number }[];
};

export type LabPathResult = {
  node_path: string[];
  expanded_order: string[];
  distance_meters: number;
  estimated_seconds: number;
  solver_name: string;
  nodes_expanded: number;
  computation_time_ns: number;
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

export function getLabGraph(identity: DemoIdentity): Promise<LabGraph> {
  return request<LabGraph>("/api/v1/lab/graph", { identity });
}

export function runLabPath(
  identity: DemoIdentity,
  body: {
    origin: string;
    destination: string;
    solver: "astar" | "dijkstra";
    objective: "time" | "distance";
    trace: boolean;
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
  },
): Promise<LabTspResult> {
  return request<LabTspResult>("/api/v1/lab/tsp", {
    method: "POST",
    identity,
    body,
  });
}
