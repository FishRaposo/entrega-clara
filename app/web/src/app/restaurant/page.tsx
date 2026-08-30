import { PlatformShell } from "../../components/platform-shell";
import { brazilMarket } from "../../lib/market-config";

export default function RestaurantPage() {
  return <PlatformShell market={brazilMarket}><section className="role-page"><p className="eyebrow">Prévia do restaurante</p><h1>Sinais de preparo para a hora do almoço.</h1><p>Esta rota representa a visão operacional do restaurante e não recebe pedidos reais.</p></section></PlatformShell>;
}
