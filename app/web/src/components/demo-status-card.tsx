"use client";

import { useEffect, useState } from "react";

import {
  advanceDemo,
  type DemoScenario,
  getDemoScenario,
  resetDemo,
} from "../lib/api-client";

type DemoStatusCardProps = {
  locationLabel: string;
};

const stageLabels: Record<string, string> = {
  placed: "feito",
  confirmed: "confirmado",
  preparing: "em preparo",
  ready_for_pickup: "pronto para retirada",
  courier_assigned: "entregador atribuído",
  picked_up: "retirado",
  en_route: "a caminho",
  delivered: "entregue",
  rated: "avaliado",
};

export function DemoStatusCard({ locationLabel }: DemoStatusCardProps) {
  const [scenario, setScenario] = useState<DemoScenario | null>(null);
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

  const runCommand = async (command: () => Promise<DemoScenario>) => {
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

  const stage = scenario
    ? (stageLabels[scenario.active_order.state] ?? scenario.active_order.state)
    : "carregando";

  return (
    <section aria-labelledby="demo-status-title" className="demo-status-card">
      <div className="status-label" role="status">Estado simulado · API local</div>
      <h2 id="demo-status-title">Hora do almoço: Demo Kitchen</h2>
      {scenario ? <p>Pedido #{scenario.active_order.id}</p> : null}
      <p>Estado atual: <strong>{stage}</strong>.</p>
      {scenario ? <p className="quiet">Relógio simulado: {scenario.clock_minutes} min.</p> : null}
      <p className="quiet">Local de referência configurado: {locationLabel}.</p>
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      <div className="demo-actions">
        <button
          disabled={pending}
          onClick={() => void runCommand(() => advanceDemo(1))}
          type="button"
        >
          Avançar cenário
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
      <p className="quiet">Esta demonstração de portfólio não coleta dados pessoais nem processa pagamentos ou localização reais.</p>
    </section>
  );
}
