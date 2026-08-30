import Link from "next/link";
import type { ReactNode } from "react";
import type { MarketConfig } from "../lib/market-config";
import { RoleSwitcher } from "./role-switcher";

type PlatformShellProps = {
  children: ReactNode;
  market: MarketConfig;
};

export function PlatformShell({ children, market }: PlatformShellProps) {
  return (
    <div className="site-shell">
      <a className="skip-link" href="#main-content">Pular para o conteúdo</a>
      <header className="site-header">
        <Link className="brand" href="/" aria-label="Início da Entrega Clara">Entrega Clara</Link>
        <div className="market-badge" aria-label={`Mercado: ${market.id}`}>{market.locale} · {market.currency} · {market.location.label}</div>
        <Link className="demo-link" href="/demo">Abrir modo demonstração</Link>
      </header>
      <main id="main-content">{children}</main>
      <footer className="site-footer">
        <RoleSwitcher />
        <p>Brasil como mercado inicial, com configuração para outros mercados. Contexto de privacidade: {market.privacyRegime}.</p>
      </footer>
    </div>
  );
}
