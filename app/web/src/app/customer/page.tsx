import { PlatformShell } from "../../components/platform-shell";
import { brazilMarket } from "../../lib/market-config";

export default function CustomerPage() {
  return <PlatformShell market={brazilMarket}><section className="role-page"><p className="eyebrow">Prévia do cliente</p><h1>Confiança no pedido, sem uma finalização de compra real.</h1><p>Esta prévia navegável representa o pedido e o acompanhamento do cliente no modo demonstração.</p></section></PlatformShell>;
}
