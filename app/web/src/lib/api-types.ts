export type MoneyTotals = {
  subtotal_minor: number;
  discount_minor: number;
  delivery_fee_minor: number;
  total_minor: number;
  currency: string;
};

export type RestaurantSummary = {
  id: string;
  name: string;
  cuisine: string;
  description: string;
  available: boolean;
  delivery_fee_minor: number;
  address_label: string;
  latitude: number;
  longitude: number;
};

export type MenuItem = {
  id: string;
  restaurant_id: string;
  name: string;
  description: string;
  category: string;
  price_minor: number;
  currency: string;
  available: boolean;
};

export type CartLine = {
  id: string;
  menu_item_id: string;
  quantity: number;
  observation: string;
};

export type Cart = MoneyTotals & {
  id: string | null;
  restaurant_id: string | null;
  coupon_code: string | null;
  version: number;
  lines: CartLine[];
};

export type Address = {
  id: string;
  label: string;
  formatted: string;
  latitude: number;
  longitude: number;
};

export type Payment = {
  id: string;
  order_id: string;
  method: string;
  status: string;
  safe_reference: string;
  failure_code: string | null;
  created_at: string | null;
};

export type Delivery = {
  id: string;
  order_id: string;
  courier_id: string | null;
  status: string;
  version: number;
  batch_id?: string | null;
};

export type DeliveryBatch = {
  id: string;
  courier_id: string;
  delivery_ids: string[];
  status: string;
  created_at: string | null;
};

export type RouteStop = {
  kind: string;
  ref_id: string;
  label: string;
  latitude: number;
  longitude: number;
  sequence: number;
  planned_arrival_at?: string | null;
  promised_until?: string | null;
};

export type RoutePlan = {
  id: string;
  graph_id: string;
  graph_version: string;
  stops: RouteStop[];
  segments: {
    from_label: string;
    to_label: string;
    distance_meters: number;
    estimated_seconds: number;
  }[];
  geometry: { type: string; coordinates: [number, number][] } | null;
  distance_meters: number;
  estimated_seconds: number;
  solver_name: string;
  solver_version: string;
  computation_time_ns?: number;
  warnings: string[];
  objective?: string;
  batch_id?: string | null;
  /** Batch tours only: the same matrix solved by a cheap heuristic, as a baseline. */
  baseline_solver_name?: string | null;
  baseline_cost?: number | null;
  departure_at?: string | null;
  arrival_at?: string | null;
  traffic_profile_id?: string | null;
  wait_seconds?: number;
  lateness_seconds?: number;
  capacity_used?: number;
};

export type OrderSummary = {
  id: string;
  restaurant_id: string;
  state: string;
  total_minor: number;
  currency: string;
  version: number;
  created_at: string | null;
};

export type OrderItem = {
  menu_item_id: string;
  name: string;
  unit_price_minor: number;
  quantity: number;
  observation: string;
};

export type Order = OrderSummary & {
  customer_id: string;
  address_label: string;
  coupon_code: string | null;
  items: OrderItem[];
  payment: Payment | null;
  delivery: Delivery | null;
  route: RoutePlan | null;
};

export type TrackingPosition = {
  id: string;
  delivery_id: string;
  sequence: number;
  latitude: number;
  longitude: number;
  occurred_at: string | null;
};

export type TrackingView = {
  order_id: string;
  order_status: string;
  delivery_status: string | null;
  route: RoutePlan | null;
  last_known_location: { latitude: number; longitude: number } | null;
  positions: TrackingPosition[];
};

export type Notification = {
  id: string;
  order_id: string;
  type: string;
  message: string;
  read: boolean;
  created_at: string | null;
};

export type DomainEvent = {
  id: string;
  type: string;
  aggregate_type: string;
  aggregate_id: string;
  actor_id: string;
  actor_role: string;
  correlation_id: string;
  sequence: number;
  occurred_at: string | null;
  payload: Record<string, unknown>;
};

export type CourierProfile = {
  id: string;
  name: string;
  status: string;
  latitude: number;
  longitude: number;
  version: number;
};

export type CheckoutResult = {
  order_id: string;
  state: string;
  total_minor: number;
  currency: string;
  payment: Payment;
  replayed: boolean;
};

export type Metrics = Record<string, unknown> & {
  orders_by_state?: Record<string, number>;
  deliveries_by_status?: Record<string, number>;
  totals?: Record<string, number>;
};

export type DemoSnapshot = {
  scenario_id: string;
  description: string;
  clock: string;
  run_id: number;
  step_index: number;
  steps_total: number;
  remaining_steps: number;
  order: { id: string; state: string; total_minor: number } | null;
  delivery: { id: string; status: string; courier_id: string | null } | null;
  route: {
    id: string;
    graph_id: string;
    distance_meters: number;
    estimated_seconds: number;
  } | null;
  tracking_points: number;
  notifications: string[];
};
