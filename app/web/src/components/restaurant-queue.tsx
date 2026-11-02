"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, listRestaurantQueue, restaurantCommand } from "../lib/api-client";
import type { OrderSummary } from "../lib/api-types";
import { formatBRL, orderStateLabel } from "../lib/format";
import { DEMO_IDENTITIES } from "../lib/identities";

const ID = DEMO_IDENTITIES.restaurant;

const NEXT_ACTION: Record<string, { action: "confirm" | "prepare" | "ready"; label: string }> = {
  placed: { action: "confirm", label: "Confirmar pedido" },
  confirmed: { action: "prepare", label: "Iniciar preparo" },
  preparing: { action: "ready", label: "Pronto para retirada" },
};

export function RestaurantQueue() {
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setOrders((await listRestaurantQueue(ID)).orders);
    } catch {
      setError(
        "Não foi possível carregar a fila. Verifique se a API local está ativa e tente novamente.",
      );
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 5000);
    return () => clearInterval(timer);
  }, [refresh]);

  const act = async (orderId: string, action: "confirm" | "prepare" | "ready") => {
    setPending(true);
    setError(null);
    try {
      await restaurantCommand(ID, orderId, action);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "A ação não foi concluída. Tente novamente.");
    } finally {
      setPending(false);
    }
  };

  const active = orders.filter((o) => !["delivered", "cancelled", "rated"].includes(o.state));
  const finished = orders.filter((o) => ["delivered", "cancelled", "rated"].includes(o.state));

  return (
    <section className="role-page" aria-labelledby="restaurant-title">
      <p className="eyebrow">Restaurante · Seu Manoel</p>
      <h1 id="restaurant-title">Fila de produção</h1>
      {error ? <p role="alert">{error}</p> : null}
      {active.length === 0 ? <p>Nenhum pedido na fila no momento.</p> : null}
      <ul className="queue-grid">
        {active.map((order) => {
          const next = NEXT_ACTION[order.state];
          return (
            <li key={order.id} className="panel">
              <strong>Pedido {order.id}</strong> · {formatBRL(order.total_minor)}
              <br />
              Estado: <strong>{orderStateLabel(order.state)}</strong>
              {next ? (
                <div className="demo-actions">
                  <button type="button" disabled={pending} onClick={() => void act(order.id, next.action)}>
                    {next.label}
                  </button>
                </div>
              ) : (
                <p className="quiet">Aguardando o entregador.</p>
              )}
            </li>
          );
        })}
      </ul>
      {finished.length > 0 ? (
        <details>
          <summary>Histórico ({finished.length})</summary>
          <ul className="stacked-list">
            {finished.map((order) => (
              <li key={order.id}>
                {order.id} · {orderStateLabel(order.state)} · {formatBRL(order.total_minor)}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      <button type="button" className="secondary-button" onClick={() => void refresh()}>
        Atualizar fila
      </button>
    </section>
  );
}
