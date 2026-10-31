"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  courierCommand,
  getActiveDelivery,
  getTracking,
  listDeliveryOffers,
  postCourierLocation,
  setCourierAvailability,
} from "../lib/api-client";
import type { Delivery, TrackingView } from "../lib/api-types";
import { deliveryStatusLabel } from "../lib/format";
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
  const [active, setActive] = useState<Delivery | null>(null);
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
      setActive(activeResult.delivery);
      if (activeResult.delivery) {
        setTracking(await getTracking(ID, activeResult.delivery.order_id));
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

  const nextSequence = (tracking?.positions.length ?? 0) + 1;

  const sendLocation = () =>
    run(async () => {
      if (!active || !tracking?.route?.geometry) return;
      const coords = tracking.route.geometry.coordinates;
      const index = Math.min(nextSequence - 1, coords.length - 1);
      const [longitude, latitude] = coords[index];
      await postCourierLocation(ID, active.id, nextSequence, latitude, longitude);
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

      {active ? (
        <div className="panel">
          <h2>Entrega ativa {active.id}</h2>
          <p>
            Pedido {active.order_id} · status{" "}
            <strong>{deliveryStatusLabel(active.status)}</strong>
          </p>
          <DeliveryMap route={tracking?.route ?? null} lastKnown={tracking?.last_known_location} />
          <div className="demo-actions">
            {active.status === "en_route" ? (
              <button type="button" disabled={pending} onClick={() => void sendLocation()}>
                Enviar ponto GPS (#{nextSequence})
              </button>
            ) : null}
            {NEXT_STEP[active.status] ? (
              <button
                type="button"
                disabled={pending}
                onClick={() => void run(() => courierCommand(ID, active.id, NEXT_STEP[active.status].action))}
              >
                {NEXT_STEP[active.status].label}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="panel">
        <h2>Ofertas abertas</h2>
        {offers.length === 0 ? <p>Nenhuma oferta no momento.</p> : null}
        <ul className="stacked-list">
          {offers.map((delivery) => (
            <li key={delivery.id}>
              Entrega {delivery.id} · pedido {delivery.order_id}
              <div className="demo-actions">
                <button
                  type="button"
                  disabled={pending || active !== null}
                  onClick={() => void run(() => courierCommand(ID, delivery.id, "accept"))}
                >
                  Aceitar entrega
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>
      <button type="button" className="secondary-button" onClick={() => void refresh()}>
        Atualizar
      </button>
    </section>
  );
}
