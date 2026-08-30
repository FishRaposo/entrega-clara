import Link from "next/link";
import { PlatformShell } from "../components/platform-shell";
import { brazilMarket } from "../lib/market-config";

export default function HomePage() {
  return (
    <PlatformShell market={brazilMarket}>
      <section className="hero" aria-labelledby="hero-title">
        <p className="eyebrow">Operação de delivery com o Brasil como mercado inicial</p>
        <h1 id="hero-title">Uma hora do almoço visível com clareza em cada papel.</h1>
        <p className="lede">Entrega Clara é uma demonstração de portfólio compacta para acompanhar um pedido desde a finalização até o preparo, a retirada e a entrega.</p>
        <Link className="primary-button" href="/demo">Explorar modo demonstração</Link>
      </section>
      <section className="feature-grid" aria-label="Destaques do produto">
        <article><h2>Clareza para clientes</h2><p>Acompanhe uma jornada determinística sem criar uma conta.</p></article>
        <article><h2>Visão operacional</h2><p>Veja as superfícies de produto para restaurante, entregador e administração.</p></article>
        <article><h2>Limite preparado para mercados</h2><p>Idioma, moeda, pagamentos, localização e privacidade vêm da configuração de mercado.</p></article>
      </section>
    </PlatformShell>
  );
}
