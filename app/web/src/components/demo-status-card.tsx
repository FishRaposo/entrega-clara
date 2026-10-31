"use client";

import { useEffect, useState } from "react";

import {
  advanceDemo,
  advanceDemoClock,
  getDemoScenario,
  resetDemo,
} from "../lib/api-client";
import type { DemoSnapshot } from "../lib/api-types";
import { deliveryStatusLabel, formatBRL, orderStateLabel } from "../lib/format";

type DemoStatusCardProps = {
  locationLabel: string;
};

export function DemoStatusCard({ locationLabel }: DemoStatusCardProps) {
  const [scenario, setScenario] = useState<DemoSnapshot | null>(null);
  const [pending, setPending] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getDemoScenario().then(
      (snapshot) => {
        if (active) {
          setScenario(snapshot);
          setPending(false);
        }
      },
      () => {
        if (active) {
          setErrorMessage("O cenário não está disponível. Confirme se a API local está ativa.");
          setPending(false);
        }
      },
    );
    return () => {
      active = false;
    };
  }, []);

  const runCommand = async (command: () => Promise<DemoSnapshot>) => {
    setPending(true);
    setErrorMessage(null);
    try {
      setScenario(await command());
    } catch {
      setErrorMessage("Não foi possível atualizar o cenário. Tente novamente.");
    } finally {
      setPending(false);
    }
  };

  return (
    <section aria-labelledby="demo-status-title" className="demo-status-card">
      <div className="status-label" role="status">Cenário guiado · API local</div>
      <h2 id="demo-status-title">Hora do almoço: {scenario?.scenario_id ?? "…"}</h2>
      {scenario?.order ? (
        <p>
          Pedido #{scenario.order.id} —{" "}
          <strong>{orderStateLabel(scenario.order.state)}</strong> ·{" "}
          {formatBRL(scenario.order.total_minor)}
        </p>
      ) : (
        <p>Pedido ainda não iniciado.</p>
      )}
      {scenario?.delivery ? (
        <p>
          Entrega {scenario.delivery.id}: {deliveryStatusLabel(scenario.delivery.status)}
          {scenario.delivery.courier_id ? ` · ${scenario.delivery.courier_id}` : ""}
        </p>
      ) : null}
      {scenario?.route ? (
        <p className="quiet">
          Rota {(scenario.route.distance_meters / 1000).toFixed(1)} km · ~
          {Math.max(1, Math.round(scenario.route.estimated_seconds / 60))} min
        </p>
      ) : null}
      {scenario ? (
        <p className="quiet">
          Passo {scenario.step_index}/{scenario.steps_total} · restantes {scenario.remaining_steps} ·
          relógio {new Date(scenario.clock).toLocaleTimeString("pt-BR")}
        </p>
      ) : null}
      {scenario && scenario.notifications.length > 0 ? (
        <details>
          <summary>Notificações ({scenario.notifications.length})</summary>
          <ul className="stacked-list">
            {scenario.notifications.map((message, index) => (
              <li key={index}>{message}</li>
            ))}
          </ul>
        </details>
      ) : null}
      <p className="quiet">Local de referência configurado: {locationLabel}.</p>
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      <div className="demo-actions">
        <button
          disabled={pending || (scenario?.remaining_steps ?? 0) === 0}
          onClick={() => void runCommand(() => advanceDemo(1))}
          type="button"
        >
          Avançar passo
        </button>
        <button
          className="secondary-button"
          disabled={pending}
          onClick={() => void runCommand(() => advanceDemoClock(5))}
          type="button"
        >
          +5 min simulados
        </button>
        <button
          className="secondary-button"
          disabled={pending}
          onClick={() => void runCommand(resetDemo)}
          type="button"
        >
          Reiniciar cenário
        </button>
      </div>
      <p className="quiet">Este cenário executa os mesmos comandos das telas de papel: sacola, checkout, preparo e entrega.</p>
    </section>
  );
}
