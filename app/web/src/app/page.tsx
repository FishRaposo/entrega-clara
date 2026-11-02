import Link from "next/link";
import labTrace from "../../../../docs/benchmarks/lab-trace.json";
import { PlatformShell } from "../components/platform-shell";
import { RouteProof } from "../components/route-proof";
import { brazilMarket } from "../lib/market-config";

export default function HomePage() {
  const alt = labTrace.solvers.alt;
  const dijkstra = labTrace.solvers.dijkstra;
  const minutes = Math.floor(alt.estimated_seconds / 60);
  const seconds = Math.round(alt.estimated_seconds % 60);
  const duration = `${minutes} min ${seconds} s`;

  return (
    <PlatformShell market={brazilMarket}>
      <section className="landing-hero" aria-labelledby="hero-title">
        <div className="landing-hero-copy">
          <p className="eyebrow">Operação de delivery com o Brasil como mercado inicial</p>
          <h1 id="hero-title">Uma hora do almoço visível com clareza em cada papel.</h1>
          <p className="lede">Entrega Clara é uma demonstração de portfólio compacta para acompanhar um pedido desde a finalização até o preparo, a retirada e a entrega.</p>
          <p className="landing-proof-line">
            No mesmo grafo de São Paulo, o Dijkstra abre {dijkstra.expanded_order.length} nós. O A*
            + ALT abre {alt.expanded_order.length}. O caminho e o custo são os mesmos: {duration}.
          </p>
          <div className="landing-hero-actions">
            <Link className="primary-button" href="/demo">Explorar modo demonstração</Link>
          </div>
        </div>
        <figure className="landing-hero-artifact">
          <RouteProof trace={labTrace} />
          <figcaption>
            A rota do laboratório: A origem, B destino. Os pontos âmbar são nós expandidos pelo
            Dijkstra; a linha verde é o caminho que os dois encontram.{" "}
            <Link className="proof-link" href="/lab">Ver a comparação completa</Link>.
          </figcaption>
        </figure>
      </section>
      <section className="landing-support" aria-label="Também nesta demo">
        <p>
          Também nesta demo: fila do restaurante, rota do entregador, visão de operações e
          configuração de mercado.
        </p>
      </section>
    </PlatformShell>
  );
}
