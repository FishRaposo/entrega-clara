"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getOperationsMetrics,
  listOperationsCouriers,
  listOperationsEvents,
  listOperationsOrders,
  listOperationsTimeline,
  type OrderTimeline,
} from "../lib/api-client";
import type { CourierProfile, DomainEvent, Metrics, OrderSummary } from "../lib/api-types";
import { deliveryStatusLabel, formatBRL, orderStateLabel } from "../lib/format";
import { DEMO_IDENTITIES } from "../lib/identities";

const ID = DEMO_IDENTITIES.operations;

export function OperationsPanel() {
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [events, setEvents] = useState<DomainEvent[]>([]);
  const [couriers, setCouriers] = useState<CourierProfile[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [timeline, setTimeline] = useState<OrderTimeline[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [orderList, eventList, courierList, metricsView, timelineView] =
        await Promise.all([
          listOperationsOrders(ID),
          listOperationsEvents(ID),
          listOperationsCouriers(ID),
          getOperationsMetrics(ID),
          listOperationsTimeline(ID),
        ]);
      setOrders(orderList.orders);
      setEvents(eventList.events.slice(-15).reverse());
      setCouriers(courierList.couriers);
      setMetrics(metricsView);
      setTimeline(timelineView.orders);
    } catch {
      setError(
        "Não foi possível carregar a visão operacional. Verifique se a API local está ativa e tente novamente.",
      );
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 5000);
    return () => clearInterval(timer);
  }, [refresh]);

  return (
    <section className="role-page" aria-labelledby="ops-title">
      <p className="eyebrow">Operações</p>
      <h1 id="ops-title">Visão da plataforma</h1>
      {error ? <p role="alert">{error}</p> : null}

      <div className="panel-grid">
        {metrics ? (
          <div className="panel">
            <h2>Métricas</h2>
            <ul className="stacked-list">
              {Object.entries(metrics.orders_by_state ?? {}).map(([state, count]) => (
                <li key={state}>
                  {orderStateLabel(state)}: <strong>{count}</strong>
                </li>
              ))}
              {Object.entries(metrics.deliveries_by_status ?? {}).map(([status, count]) => (
                <li key={status}>
                  Entregas {deliveryStatusLabel(status)}: <strong>{count}</strong>
                </li>
              ))}
            </ul>
            {metrics.counters?.length ? (
              <>
                <h3>Processo</h3>
                <ul className="stacked-list">
                  {metrics.counters
                    .filter((counter) => counter.name.startsWith("entrega_routing"))
                    .slice(0, 4)
                    .map((counter) => (
                      <li key={`${counter.name}-${JSON.stringify(counter.labels)}`}>
                        {counter.name.replace("entrega_", "")}
                        {counter.labels?.kind ? ` (${String(counter.labels.kind)})` : ""}:{" "}
                        <strong>{counter.value}</strong>
                      </li>
                    ))}
                  <li>
                    requisições HTTP:{" "}
                    <strong>
                      {(metrics.counters ?? [])
                        .filter((counter) => counter.name === "entrega_http_requests_total")
                        .reduce((total, counter) => total + (counter.value ?? 0), 0)}
                    </strong>
                  </li>
                </ul>
              </>
            ) : null}
          </div>
        ) : null}

        <div className="panel">
          <h2>Pedidos ({orders.length})</h2>
          <ul className="stacked-list">
            {orders.map((order) => (
              <li key={order.id}>
                {order.id} · {orderStateLabel(order.state)} · {formatBRL(order.total_minor)}
              </li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <h2>Entregadores</h2>
          <ul className="stacked-list">
            {couriers.map((courier) => (
              <li key={courier.id}>
                {courier.name} · {deliveryStatusLabel(courier.status)}
              </li>
            ))}
          </ul>
        </div>

        <div className="panel timeline-panel">
          <h2>Cronologia por pedido</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Pedido</th>
                <th scope="col">Estágios</th>
                <th scope="col">ETA (s)</th>
                <th scope="col">Real (s)</th>
                <th scope="col">Erro (s)</th>
              </tr>
            </thead>
            <tbody>
              {timeline.map((row) => (
                <tr key={row.order_id}>
                  <td>{row.order_id}</td>
                  <td>
                    {row.stages
                      .map((stage) => `${stage.stage} ${Math.round(stage.duration_seconds)}s`)
                      .join(" → ")}
                  </td>
                  <td>{row.eta_estimated_seconds ?? "—"}</td>
                  <td>{row.eta_actual_seconds ?? "—"}</td>
                  <td>{row.eta_error_seconds ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel ops-events">
          <h2>Eventos recentes</h2>
          {events.length > 0 ? (
            <ol className="event-feed" tabIndex={0} aria-label="Eventos recentes, região rolável">
              {events.map((event) => (
                <li key={event.id}>
                  <code>{event.type}</code> · {event.actor_role} ·{" "}
                  {event.occurred_at?.slice(11, 19) ?? ""}
                </li>
              ))}
            </ol>
          ) : (
            <p className="quiet">Nenhum evento recente.</p>
          )}
        </div>
      </div>
      <button type="button" className="secondary-button" onClick={() => void refresh()}>
        Atualizar painel
      </button>
    </section>
  );
}
