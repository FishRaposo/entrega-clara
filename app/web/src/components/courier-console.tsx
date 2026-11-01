"use client";

import { useCallback, useEffect, useState } from "react";

import {
  acceptBatch,
  ApiError,
  courierCommand,
  getActiveDelivery,
  getTracking,
  listDeliveryOffers,
  advanceRouteLocation,
  setCourierAvailability,
} from "../lib/api-client";
import type { Delivery, TrackingView } from "../lib/api-types";
import { deliveryStatusLabel, formatDuration } from "../lib/format";
import { DEMO_IDENTITIES } from "../lib/identities";
import { DeliveryMap } from "./delivery-map";

const ID = DEMO_IDENTITIES.courier;

const NEXT_STEP: Record<string, { action: "pickup" | "start" | "complete"; label: string }> = {
  assigned: { action: "pickup", label: "Retirar no restaurante" },
  picked_up: { action: "start", label: "Iniciar rota" },
  en_route: { action: "complete", label: "Concluir entrega" },
};

export function CourierConsole() {
  const [available, setAvailable] = useState<boolean | null>(null);
  const [offers, setOffers] = useState<Delivery[]>([]);
  const [actives, setActives] = useState<Delivery[]>([]);
  const [activeRoute, setActiveRoute] = useState<TrackingView["route"] | null>(null);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [tracking, setTracking] = useState<TrackingView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [offerList, activeResult] = await Promise.all([
        listDeliveryOffers(ID),
        getActiveDelivery(ID),
      ]);
      setOffers(offerList.deliveries.filter((d): d is Delivery => d !== null));
      setActives(activeResult.deliveries);
      setBatchId(activeResult.batch?.id ?? null);
      setActiveRoute(activeResult.route);
      const first = activeResult.deliveries[0];
      if (first) {
        setTracking(await getTracking(ID, first.order_id));
      } else {
        setTracking(null);
      }
    } catch {
      setError("Não foi possível carregar as entregas. A API local está ativa?");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const run = async (action: () => Promise<unknown>) => {
    setPending(true);
    setError(null);
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "A ação falhou.");
    } finally {
      setPending(false);
    }
  };

  const toggleAvailability = () =>
    run(async () => {
      const next = !(available ?? false);
      const result = await setCourierAvailability(ID, next);
      setAvailable(result.status === "available");
    });

  const sendLocation = (delivery: Delivery) =>
    run(async () => {
      await advanceRouteLocation(ID, delivery.id);
    });

  return (
    <section className="role-page" aria-labelledby="courier-title">
      <p className="eyebrow">Entregadora · Ana Entregas</p>
      <h1 id="courier-title">Console de entregas</h1>
      {error ? <p role="alert">{error}</p> : null}

      <div className="panel">
        <p>
          Disponibilidade:{" "}
          <strong>{available ? "disponível" : available === false ? "indisponível" : "…"}</strong>
        </p>
        <button type="button" disabled={pending} onClick={() => void toggleAvailability()}>
          {available ? "Ficar indisponível" : "Ficar disponível"}
        </button>
      </div>

      {actives.length > 0 ? (
        <div className="panel">
          <h2>
            {batchId ? `Lote ativo ${batchId}` : `Entrega ativa ${actives[0].id}`}
          </h2>
          {activeRoute?.stops ? (
            <ol className="stacked-list" aria-label="Sequência do percurso">
              {activeRoute.stops.map((stop) => {
                const delivery = actives.find((d) => d.id === stop.ref_id);
                return (
                  <li key={`${stop.sequence}-${stop.ref_id}`}>
                    <strong>#{stop.sequence}</strong>{" "}
                    {stop.kind === "pickup" ? "Retirada" : "Entrega"} ·{" "}
                    {stop.label}
                    {delivery ? ` (${deliveryStatusLabel(delivery.status)})` : ""}
                  </li>
                );
              })}
            </ol>
          ) : null}
          {activeRoute?.baseline_cost != null ? (
            <p className="muted">
              {formatDuration(activeRoute.estimated_seconds)} na ordem exata
              {activeRoute.baseline_solver_name
                ? ` · ${activeRoute.baseline_solver_name}: ${formatDuration(activeRoute.baseline_cost)}`
                : ""}
              {activeRoute.computation_time_ns
                ? ` · busca em ${(activeRoute.computation_time_ns / 1e6).toFixed(1)} ms`
                : ""}
            </p>
          ) : null}
          <DeliveryMap route={tracking?.route ?? activeRoute} lastKnown={tracking?.last_known_location} />
          {actives.map((delivery) => (
            <div key={delivery.id} className="demo-actions">
              <span>
                Pedido {delivery.order_id} ·{" "}
                <strong>{deliveryStatusLabel(delivery.status)}</strong>
              </span>
              {delivery.status === "en_route" ? (
                <button type="button" disabled={pending} onClick={() => void sendLocation(delivery)}>
                  Enviar ponto GPS
                </button>
              ) : null}
              {NEXT_STEP[delivery.status] ? (
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => void run(() => courierCommand(ID, delivery.id, NEXT_STEP[delivery.status].action))}
                >
                  {NEXT_STEP[delivery.status].label} — {delivery.id}
                </button>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}

      <div className="panel">
        <h2>Ofertas abertas</h2>
        {offers.length === 0 ? <p>Nenhuma oferta no momento.</p> : null}
        <ul className="stacked-list">
          {offers.map((delivery) => (
            <li key={delivery.id}>
              <label>
                <input
                  type="checkbox"
                  checked={selected.has(delivery.id)}
                  disabled={actives.length > 0}
                  onChange={() => {
                    setSelected((prev) => {
                      const next = new Set(prev);
                      if (next.has(delivery.id)) {
                        next.delete(delivery.id);
                      } else if (next.size < 3) {
                        next.add(delivery.id);
                      }
                      return next;
                    });
                  }}
                />{" "}
                Entrega {delivery.id} · pedido {delivery.order_id}
              </label>
              <div className="demo-actions">
                <button
                  type="button"
                  disabled={pending || actives.length > 0}
                  onClick={() => void run(() => courierCommand(ID, delivery.id, "accept"))}
                >
                  Aceitar entrega
                </button>
              </div>
            </li>
          ))}
        </ul>
        {offers.length >= 2 ? (
          <button
            type="button"
            disabled={pending || actives.length > 0 || selected.size < 2}
            onClick={() =>
              run(async () => {
                await acceptBatch(ID, Array.from(selected));
                setSelected(new Set());
              })
            }
          >
            Aceitar lote ({selected.size} selecionadas)
          </button>
        ) : null}
      </div>
      <button type="button" className="secondary-button" onClick={() => void refresh()}>
        Atualizar
      </button>
    </section>
  );
}
