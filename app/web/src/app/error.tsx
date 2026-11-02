"use client";

import Link from "next/link";

import { PlatformShell } from "../components/platform-shell";
import { brazilMarket } from "../lib/market-config";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <PlatformShell market={brazilMarket}>
      <section className="page-intro">
        <p className="eyebrow">Falha inesperada</p>
        <h1>Não foi possível abrir esta tela.</h1>
        <p>O restante da demonstração continua disponível. Tente de novo ou volte à página inicial.</p>
        <div className="landing-hero-actions">
          <button type="button" className="primary-button" onClick={reset}>
            Tentar novamente
          </button>
          <Link className="proof-link" href="/">
            Voltar ao início
          </Link>
        </div>
      </section>
    </PlatformShell>
  );
}
