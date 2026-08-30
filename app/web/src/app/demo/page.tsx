import { DemoStatusCard } from "../../components/demo-status-card";
import { PlatformShell } from "../../components/platform-shell";
import { RoleSwitcher } from "../../components/role-switcher";
import { brazilMarket } from "../../lib/market-config";

export default function DemoPage() {
  return (
    <PlatformShell market={brazilMarket}>
      <section className="page-intro" aria-labelledby="demo-title">
        <p className="eyebrow">Modo demonstração</p>
        <h1 id="demo-title">Hora do almoço, reproduzida com segurança.</h1>
        <p>Explore o cenário fixo de entrega usando os controles da API local.</p>
      </section>
      <DemoStatusCard locationLabel={brazilMarket.location.label} />
      <RoleSwitcher />
    </PlatformShell>
  );
}
