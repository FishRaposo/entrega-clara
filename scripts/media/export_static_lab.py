"""Bake the algorithm lab into one self-contained HTML page.

The result has no framework, no network access and no API: it replays the
committed traces in ``docs/benchmarks/lab-trace.json``, adds the day-long ETA
curve computed from the committed traffic profile, and prints the published
TSP benchmark table. Served from GitHub Pages it gives a reviewer a clickable
lab without cloning anything.

    python scripts/media/export_static_lab.py
    # writes site/index.html
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TRACE_PATH = ROOT / "docs" / "benchmarks" / "lab-trace.json"
BENCH_PATH = ROOT / "docs" / "benchmarks" / "routing.json"
OUTPUT = ROOT / "site" / "index.html"


def _traffic_curve(trace: dict[str, Any]) -> dict[str, Any] | None:
    """24 hourly ETAs for the traced route, from the committed profile."""
    sys.path.insert(0, str(ROOT / "app" / "backend" / "src"))
    try:
        from delivery_platform.routing.graph import load_graph
        from delivery_platform.routing.path import DijkstraPathSolver, PathProblem
        from delivery_platform.routing.time_dependent import (
            TimeDependentAStarPathSolver,
        )
        from delivery_platform.routing.time_profile import load_profile

        graph = load_graph(ROOT / "data" / "graph" / "sao-paulo-centro-osm.json")
        profile = load_profile(ROOT / "data" / "graph" / "traffic-profile.json")
        origin = trace["ids"][trace["origin"]]
        destination = trace["ids"][trace["destination"]]
        free_flow = DijkstraPathSolver().solve(
            PathProblem(graph, origin, destination, "time")
        ).estimated_seconds
        solver = TimeDependentAStarPathSolver()
        # Local midnight of a fixed reference day, so "hour 12" means 12h local
        # (the profile shifts the epoch by its UTC offset).
        midnight = datetime(2026, 1, 1, tzinfo=UTC).timestamp() - profile.tz_offset_hours * 3600.0
        points = []
        for hour in range(24):
            result = solver.solve(
                PathProblem(
                    graph,
                    origin,
                    destination,
                    "time",
                    midnight + hour * 3600.0,
                    profile,
                )
            )
            points.append({"hour": hour, "seconds": round(result.estimated_seconds, 1)})
        peak = max(points, key=lambda point: point["seconds"])
        night = min(points, key=lambda point: point["seconds"])
        return {
            "profile_id": profile.profile_id,
            "source": profile.source,
            "free_flow": round(free_flow, 1),
            "points": points,
            "peak_hour": peak["hour"],
            "peak_seconds": peak["seconds"],
            "night_hour": night["hour"],
            "night_seconds": night["seconds"],
        }
    except Exception:  # noqa: BLE001 - the page must build without the backend too
        return None


def _benchmarks() -> list[dict[str, Any]]:
    if not BENCH_PATH.exists():
        return []
    document = json.loads(BENCH_PATH.read_text(encoding="utf-8"))
    return document.get("tsp_graph", document.get("tsp_random", []))


def _page(trace: dict[str, Any], traffic: dict[str, Any] | None, rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        {"trace": trace, "traffic": traffic, "benchmarks": rows},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return TEMPLATE.replace("/*__DATA__*/", payload)


TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Replay de uma corrida Dijkstra e A* + ALT sobre o centro de São Paulo, com traces commitados e benchmark de roteirização.">
<meta name="theme-color" content="#fffdf8">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%23fffdf8'/%3E%3Cpath d='M16 46 32 18l16 28' fill='none' stroke='%23b94a22' stroke-width='6' stroke-linecap='round' stroke-linejoin='round'/%3E%3Ccircle cx='16' cy='46' r='5' fill='%2312231b'/%3E%3Ccircle cx='48' cy='46' r='5' fill='%2312231b'/%3E%3C/svg%3E">
<title>Entrega Clara · laboratório de algoritmos</title>
<style>
  :root { --ink:#12231b; --muted:#52665b; --paper:#fffdf8; --surface:#f1f5ed;
          --accent:#b94a22; --accent-dark:#8f3618; --line:#c9d4c9; --focus:#0b66c3; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--paper); color:var(--ink);
         font-family:Arial, Helvetica, sans-serif; line-height:1.55; }
  .skip { position:absolute; left:1rem; top:-4rem; background:var(--ink); color:#fff;
          padding:.6rem .9rem; z-index:10; }
  .skip:focus { top:1rem; }
  a:focus-visible, button:focus-visible, select:focus-visible {
    outline:3px solid var(--focus); outline-offset:3px;
  }
  header { max-width:1100px; margin:0 auto; padding:2.2rem 1.2rem .6rem; }
  h1 { font-size:clamp(1.9rem,4vw,2.8rem); line-height:1.05; margin:.2rem 0 .4rem;
       letter-spacing:-.02em; text-wrap:balance; overflow-wrap:break-word; }
  h2 { font-size:1.15rem; line-height:1.25; margin:0 0 .5rem; }
  h3 { font-size:1.05rem; line-height:1.3; margin:.8rem 0 .3rem; }
  .eyebrow { color:var(--accent); font-size:.875rem; line-height:1.2; letter-spacing:.14em;
             text-transform:uppercase; font-weight:700; }
  .muted { color:var(--muted); font-size:.875rem; line-height:1.55; max-width:65ch; }
  main { max-width:1100px; margin:0 auto; padding:0 1.2rem 3rem; }
  .panel { background:var(--surface); border:1px solid var(--line); border-radius:.6rem; padding:1rem 1.1rem; margin:1rem 0; }
  .controls { display:flex; flex-wrap:wrap; gap:.7rem; align-items:flex-end; margin:.4rem 0 .8rem; }
  .controls label { display:flex; flex-direction:column; gap:.2rem; font-size:.875rem; line-height:1.4; }
  select, button { font:inherit; font-size:.875rem; padding:.35rem .6rem; border:1px solid var(--line);
                   border-radius:.35rem; background:var(--paper); color:inherit; min-height:44px; }
  button { cursor:pointer; transition:background-color 160ms ease, transform 160ms ease; }
  @media (hover:hover) { button:hover { background:#e8efe3; } }
  button:active { transform:translateY(1px); }
  .panels { display:grid; grid-template-columns:1fr 1fr; gap:1rem; }
  .legend { display:flex; flex-wrap:wrap; align-items:center; gap:.35rem .9rem; margin:.6rem 0 0;
            color:var(--muted); font-size:.875rem; line-height:1.4; }
  .legend .dot { width:.65rem; height:.65rem; border-radius:50%; display:inline-block;
                 border:1px solid var(--line); }
  .legend .dot.origin { background:#ffffff; }
  .legend .dot.destination { background:#b94a22; }
  .legend .dot.expanded { background:linear-gradient(90deg,#d9a441,#e2603b); }
  .legend .dot.path { background:#8ee08a; }
  @media (max-width:820px) { .panels { grid-template-columns:1fr; } }
  .card { border:1px solid var(--line); border-radius:.6rem; padding:.7rem; background:var(--paper); }
  canvas { width:100%; height:auto; display:block; border-radius:.4rem; background:#0f1720; }
  .counters { display:flex; flex-wrap:wrap; gap:.4rem 1rem; margin:.6rem 0 0; font-size:.875rem; line-height:1.4; }
  .counters dt { color:var(--muted); text-transform:uppercase; letter-spacing:.06em; font-size:.875rem; line-height:1.2; }
  .counters dd { margin:0; font-weight:700; font-variant-numeric:tabular-nums; }
  .strip { display:flex; align-items:flex-end; gap:2px; height:84px; border-bottom:1px solid var(--line); margin:.4rem 0 .2rem; }
  .strip span { flex:1; min-height:3px; background:#a9bd9f; border-top:2px solid #7d9670; border-radius:2px 2px 0 0; }
  .strip span.peak { background:var(--accent); border-top-color:var(--accent-dark); }
  .strip span.night { background:#4f6b45; border-top-color:#3c5334; }
  .strip-labels { display:flex; justify-content:space-between; color:var(--muted); font-size:.875rem; }
  table { width:100%; border-collapse:collapse; font-size:.875rem; line-height:1.4; }
  th, td { text-align:left; padding:.3rem .4rem; border-bottom:1px solid var(--line); }
  th { color:var(--muted); font-size:.875rem; line-height:1.2; text-transform:uppercase; letter-spacing:.05em; }
  .table-wrap { overflow-x:auto; }
  .table-wrap table { min-width:560px; }
  caption { text-align:left; color:var(--muted); font-size:.875rem; line-height:1.4; padding:.2rem 0; }
  @media (max-width:640px) {
    select, button { font-size:1rem; min-height:44px; }
    table { font-size:.9rem; }
    th { font-size:.875rem; }
  }
  footer { max-width:1100px; margin:0 auto; padding:0 1.2rem 2rem; color:var(--muted);
           font-size:.875rem; line-height:1.45; }
</style>
</head>
<body>
<a class="skip" href="#main">Pular para o conteúdo</a>
<header>
  <p class="eyebrow">Laboratório estático · replay de traces commitados</p>
  <h1>Duas buscas, as mesmas ruas</h1>
  <p class="muted">Replay de uma corrida real sobre o extrato OpenStreetMap do centro de São Paulo.
  Sem servidor, sem rede: os nós expandidos e o caminho vêm de <code>docs/benchmarks/lab-trace.json</code>.
  Dijkstra precisa de 167 expansões; A* + ALT precisa de 70.</p>
</header>
<main id="main">
  <section class="panel">
    <div class="controls">
      <button id="play" type="button">Reproduzir</button>
      <button id="step" type="button">Passo</button>
      <button id="reset" type="button">Reiniciar</button>
      <button id="finish" type="button">Mostrar fim</button>
      <label>Velocidade
        <select id="speed">
          <option value="8">8 nós/s</option>
          <option value="30" selected>30 nós/s</option>
          <option value="120">120 nós/s</option>
          <option value="0">instantâneo</option>
        </select>
      </label>
      <label>Esquerda
        <select id="left">
          <option value="dijkstra" selected>Dijkstra</option>
          <option value="astar">A* (linha reta)</option>
          <option value="alt">A* + ALT</option>
        </select>
      </label>
      <label>Direita
        <select id="right">
          <option value="dijkstra">Dijkstra</option>
          <option value="astar">A* (linha reta)</option>
          <option value="alt" selected>A* + ALT</option>
        </select>
      </label>
    </div>
    <div class="panels">
      <div class="card"><h2 id="left-title">Dijkstra</h2>
        <canvas id="left-canvas" width="520" height="420" role="img" aria-label="Replay da busca Dijkstra no grafo de São Paulo"></canvas>
        <dl class="counters" id="left-counters"></dl>
      </div>
      <div class="card"><h2 id="right-title">A* + ALT</h2>
        <canvas id="right-canvas" width="520" height="420" role="img" aria-label="Replay da busca A* + ALT no grafo de São Paulo"></canvas>
        <dl class="counters" id="right-counters"></dl>
      </div>
    </div>
    <p class="legend">
      <span class="dot origin" aria-hidden="true"></span> Origem
      <span class="dot destination" aria-hidden="true"></span> Destino
      <span class="dot expanded" aria-hidden="true"></span> Nós expandidos (cor do solver)
      <span class="dot path" aria-hidden="true"></span> Caminho final
    </p>
  </section>

  <section class="panel" id="traffic-panel" hidden>
    <h2>ETA ao longo do dia</h2>
    <p class="muted" id="traffic-caption"></p>
    <div class="strip" id="traffic-strip" role="img" aria-label="ETA por hora do dia"></div>
    <div class="strip-labels"><span>0h</span><span>6h</span><span>12h</span><span>18h</span><span>23h</span></div>
    <p class="muted" id="traffic-source"></p>
  </section>

  <section class="panel" id="bench-panel" hidden>
    <h2>Benchmarks publicados: matrizes de rua</h2>
    <div class="table-wrap">
      <table>
        <caption>paradas · custo e tempo por solver</caption>
        <thead><tr><th scope="col">paradas</th><th scope="col">Held-Karp</th><th scope="col">2-opt</th><th scope="col">vizinho</th><th scope="col">força bruta</th></tr></thead>
        <tbody id="bench-body"></tbody>
      </table>
    </div>
    <p class="muted">Custo = segundos de viagem na matriz real; contagens em parênteses são unidades de trabalho do solver.</p>
  </section>
</main>
<footer>
  Dados © OpenStreetMap contributors (ODbL 1.0). Perfil de trânsito sintético e determinístico.
  Traces, benchmarks e perfil são regenerados pelo repositório; esta página é gerada por
  <code>scripts/media/export_static_lab.py</code>.
</footer>
<script>
const DATA = /*__DATA__*/;
const LAB = DATA.trace;
const COLORS = { dijkstra:"#d9a441", astar:"#6fb3d6", alt:"#e2603b" };

function bounds() {
  let minLat=Infinity,maxLat=-Infinity,minLon=Infinity,maxLon=-Infinity;
  for (const [lat,lon] of LAB.nodes) {
    minLat=Math.min(minLat,lat); maxLat=Math.max(maxLat,lat);
    minLon=Math.min(minLon,lon); maxLon=Math.max(maxLon,lon);
  }
  return {minLat,maxLat,minLon,maxLon};
}
const B = bounds();
function project([lat,lon], width, height, pad) {
  const latSpan = Math.max(B.maxLat-B.minLat, 1e-6);
  const lonSpan = Math.max(B.maxLon-B.minLon, 1e-6) * Math.cos((B.minLat+B.maxLat)/2*Math.PI/180);
  const scale = Math.min((width-2*pad)/lonSpan, (height-2*pad)/latSpan);
  const x = pad + (lon-B.minLon)*Math.cos((B.minLat+B.maxLat)/2*Math.PI/180)*scale;
  const y = height - pad - (lat-B.minLat)*scale;
  return [x,y];
}

const panels = {
  left:  { solver:"dijkstra", canvas:document.getElementById("left-canvas"), title:document.getElementById("left-title"), counters:document.getElementById("left-counters") },
  right: { solver:"alt", canvas:document.getElementById("right-canvas"), title:document.getElementById("right-title"), counters:document.getElementById("right-counters") },
};
for (const panel of Object.values(panels)) {
  panel.ctx = panel.canvas.getContext("2d");
  panel.points = LAB.nodes.map((node) => project(node, panel.canvas.width, panel.canvas.height, 16));
}

function solverData(panel) { return LAB.solvers[panel.solver]; }
const maxFrames = Math.max(...Object.keys(LAB.solvers).map((key) => LAB.solvers[key].expanded_order.length));
let frame = maxFrames;
let timer = null;

function drawPanel(panel) {
  const ctx = panel.ctx, {width,height} = panel.canvas;
  const trace = solverData(panel);
  const expanded = trace.expanded_order;
  const shown = Math.min(frame, expanded.length);
  ctx.fillStyle = "#0f1720"; ctx.fillRect(0,0,width,height);

  ctx.strokeStyle = "rgba(148,190,170,.22)"; ctx.lineWidth = 1;
  ctx.beginPath();
  for (const [a,b] of LAB.edges) {
    const [x1,y1] = panel.points[a], [x2,y2] = panel.points[b];
    ctx.moveTo(x1,y1); ctx.lineTo(x2,y2);
  }
  ctx.stroke();

  ctx.fillStyle = COLORS[panel.solver];
  for (let i=0;i<shown;i+=1) {
    const [x,y] = panel.points[expanded[i]];
    ctx.beginPath(); ctx.arc(x,y,2.4,0,Math.PI*2); ctx.fill();
  }
  if (shown > 0) {
    const [x,y] = panel.points[expanded[shown-1]];
    ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 1.6;
    ctx.beginPath(); ctx.arc(x,y,5,0,Math.PI*2); ctx.stroke();
  }

  if (shown >= expanded.length) {
    ctx.strokeStyle = "#8ee08a"; ctx.lineWidth = 3; ctx.beginPath();
    trace.node_path.forEach((index, position) => {
      const [x,y] = panel.points[index];
      if (position === 0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    });
    ctx.stroke();
  }

  for (const [index,color] of [[LAB.origin,"#ffffff"],[LAB.destination,"#b94a22"]]) {
    const [x,y] = panel.points[index];
    ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x,y,6,0,Math.PI*2); ctx.fill();
    ctx.strokeStyle = "#0f1720"; ctx.lineWidth = 2; ctx.stroke();
  }

  panel.title.textContent = trace.solver_name;
  panel.canvas.setAttribute(
    "aria-label",
    "Replay da busca " + trace.solver_name + " no grafo de São Paulo; " +
      shown + " de " + expanded.length + " nós expandidos",
  );
  const seconds = shown >= expanded.length ? trace.estimated_seconds : (trace.expansion_costs[Math.max(0,shown-1)] || 0);
  panel.counters.innerHTML =
    "<div><dt>expandidos</dt><dd>" + shown + " / " + expanded.length + "</dd></div>" +
    "<div><dt>fronteira</dt><dd>" + (trace.frontier_sizes[Math.max(0,shown-1)] || 0) + "</dd></div>" +
    "<div><dt>custo parcial</dt><dd>" + formatSeconds(seconds) + "</dd></div>" +
    "<div><dt>resultado</dt><dd>" + (shown >= expanded.length ? formatSeconds(trace.estimated_seconds) : "—") + "</dd></div>";
}

function formatSeconds(value) {
  if (!value) return "0 s";
  const total = Math.round(value);
  const minutes = Math.floor(total/60);
  return minutes ? minutes + " min " + (total%60) + " s" : total + " s";
}

function draw() { for (const panel of Object.values(panels)) drawPanel(panel); }

function advance() {
  if (frame >= maxFrames) { pause(); return; }
  frame += 1; draw();
}
function play() {
  const speed = Number(document.getElementById("speed").value);
  if (speed === 0) { frame = maxFrames; draw(); return; }
  pause();
  timer = setInterval(advance, 1000/speed);
  document.getElementById("play").textContent = "Pausar";
}
function pause() {
  if (timer) { clearInterval(timer); timer = null; }
  document.getElementById("play").textContent = "Reproduzir";
}

document.getElementById("play").addEventListener("click", () => timer ? pause() : play());
document.getElementById("step").addEventListener("click", () => { pause(); advance(); });
document.getElementById("reset").addEventListener("click", () => { pause(); frame = 0; draw(); });
document.getElementById("finish").addEventListener("click", () => { pause(); frame = maxFrames; draw(); });
document.getElementById("speed").addEventListener("change", () => { if (timer) play(); });
for (const side of ["left","right"]) {
  document.getElementById(side).addEventListener("change", (event) => {
    panels[side].solver = event.target.value; draw();
  });
}

const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (!reduced) { frame = 0; draw(); play(); } else { draw(); }

const traffic = DATA.traffic;
if (traffic) {
  document.getElementById("traffic-panel").hidden = false;
  document.getElementById("traffic-caption").textContent =
    "mesma origem e destino · perfil " + traffic.profile_id +
    " · pico às " + traffic.peak_hour + "h: " + formatSeconds(traffic.peak_seconds) +
    " · madrugada às " + traffic.night_hour + "h: " + formatSeconds(traffic.night_seconds) +
    " · sem trânsito: " + formatSeconds(traffic.free_flow);
  document.getElementById("traffic-source").textContent = traffic.source;
  const ceiling = Math.max(...traffic.points.map((point) => point.seconds));
  const strip = document.getElementById("traffic-strip");
  strip.setAttribute("aria-label", "ETA por hora do dia; pico às " + traffic.peak_hour + " horas");
  for (const point of traffic.points) {
    const bar = document.createElement("span");
    bar.style.height = Math.max(8, point.seconds/ceiling*100) + "%";
    if (point.hour === traffic.peak_hour) bar.className = "peak";
    if (point.hour === traffic.night_hour) bar.className = "night";
    bar.title = point.hour + "h · " + formatSeconds(point.seconds);
    strip.appendChild(bar);
  }
}

const rows = DATA.benchmarks || [];
if (rows.length) {
  document.getElementById("bench-panel").hidden = false;
  const body = document.getElementById("bench-body");
  const cell = (entry) => {
    if (!entry || entry.skipped) return "—";
    return formatSeconds(entry.total_cost) + " (" + entry.routes_evaluated + " aval.)";
  };
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = "<th scope='row'>" + row.stops + "</th>" +
      "<td>" + cell(row.held_karp) + "</td><td>" + cell(row.two_opt) + "</td>" +
      "<td>" + cell(row.nearest_neighbor) + "</td><td>" + cell(row.brute_force) + "</td>";
    body.appendChild(tr);
  }
}
</script>
</body>
</html>
"""


def main() -> None:
    trace = json.loads(TRACE_PATH.read_text(encoding="utf-8"))
    traffic = _traffic_curve(trace)
    rows = _benchmarks()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(_page(trace, traffic, rows), encoding="utf-8")
    size_kb = OUTPUT.stat().st_size / 1024
    print(
        f"wrote {OUTPUT.relative_to(ROOT).as_posix()} ({size_kb:.0f} KB): "
        f"{len(trace['solvers'])} solvers, {len(trace['nodes'])} nodes, "
        f"{'traffic curve' if traffic else 'no traffic curve'}, {len(rows)} benchmark rows"
    )


if __name__ == "__main__":
    main()
