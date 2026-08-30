import { PlatformShell } from "../../components/platform-shell";
import { brazilMarket } from "../../lib/market-config";

export default function CourierPage() {
  return <PlatformShell market={brazilMarket}><section className="role-page"><p className="eyebrow">Prévia do entregador</p><h1>Progresso da entrega, sem localização em tempo real.</h1><p>Esta rota simulada não usa GPS, provedor de mapas ou dados de identidade do entregador.</p></section></PlatformShell>;
}
