import Link from "next/link";

import { PlatformShell } from "../components/platform-shell";
import { brazilMarket } from "../lib/market-config";

export default function NotFound() {
  return (
    <PlatformShell market={brazilMarket}>
      <section className="page-intro">
        <p className="eyebrow">Página não encontrada</p>
        <h1>Esta rota não existe.</h1>
        <p>O endereço pode ter mudado. A demonstração começa na página inicial.</p>
        <div className="landing-hero-actions">
          <Link className="primary-button" href="/">
            Voltar ao início
          </Link>
        </div>
      </section>
    </PlatformShell>
  );
}
