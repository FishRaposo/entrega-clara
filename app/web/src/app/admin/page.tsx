import { PlatformShell } from "../../components/platform-shell";
import { brazilMarket } from "../../lib/market-config";

export default function AdminPage() {
  return <PlatformShell market={brazilMarket}><section className="role-page"><p className="eyebrow">Prévia administrativa</p><h1>Acompanhamento do cenário, não administração de contas.</h1><p>Esta rota é uma superfície de navegação segura para a operação demonstrativa e não contém registros operacionais reais.</p></section></PlatformShell>;
}
