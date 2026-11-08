import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../..");
const output = path.join(repo, "docs/images/portfolio");

const dataUri = (relativePath) =>
  `data:image/png;base64,${fs.readFileSync(path.join(repo, relativePath)).toString("base64")}`;

const customer = dataUri("docs/media/customer.png");
const staticLab = dataUri("docs/media/static-lab.png");
const tradeoff = fs
  .readFileSync(path.join(repo, "docs/benchmarks/routing-city-tradeoff.svg"), "utf8")
  .replace("<svg ", '<svg viewBox="0 0 700 380" preserveAspectRatio="xMidYMid meet" ');

const css = `
  @page { size: 1000px 750px; margin: 0; }
  html, body { width: 1000px; height: 750px; margin: 0; }
  * { box-sizing: border-box; }
  body {
    background: #080b10;
    color: #f5f7fa;
    font-family: "Segoe UI", "Inter", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .card {
    position: relative;
    width: 1000px;
    height: 750px;
    padding: 52px 56px 40px;
    overflow: hidden;
    background:
      radial-gradient(800px 420px at 92% -10%, rgba(61, 220, 151, 0.16), transparent 60%),
      radial-gradient(700px 460px at -10% 110%, rgba(245, 185, 95, 0.08), transparent 60%),
      #080b10;
  }
  .eyebrow {
    font-size: 13px;
    letter-spacing: 0.18em;
    font-weight: 700;
    color: #3ddc97;
  }
  h1 {
    margin: 0 0 18px;
    font-size: 52px;
    line-height: 1.04;
    letter-spacing: -0.035em;
    font-weight: 700;
  }
  .split {
    display: grid;
    grid-template-columns: 1fr 490px;
    gap: 36px;
    align-items: center;
    margin-top: 22px;
  }
  .split h1 { font-size: 46px; }
  .sub {
    margin: 0 0 26px;
    font-size: 19px;
    line-height: 1.5;
    color: #b7c2ce;
  }
  .metrics {
    display: flex;
    gap: 30px;
  }
  .metrics b {
    display: block;
    font-size: 26px;
    letter-spacing: -0.02em;
    color: #ffffff;
  }
  .metrics span {
    display: block;
    max-width: 150px;
    margin-top: 4px;
    font-size: 12px;
    line-height: 1.35;
    color: #8b97a5;
  }
  .metrics.wide { margin-top: 8px; gap: 42px; }
  .metrics.wide b { font-size: 30px; }
  .visual {
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.13);
    border-radius: 18px;
    background: #0d131b;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
  }
  .visual img {
    display: block;
    width: 100%;
    height: 390px;
    object-fit: cover;
  }
  .caption {
    display: flex;
    justify-content: space-between;
    padding: 10px 14px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    font-size: 11px;
    color: #8b97a5;
  }
  .caption span:last-child { color: #3ddc97; }
  .chart {
    margin-top: 18px;
    padding: 14px 18px;
    border-radius: 16px;
    background: #f8fafc;
  }
  .chart svg { display: block; width: 100%; height: 270px; }
  .footer {
    position: absolute;
    right: 56px;
    bottom: 28px;
    left: 56px;
    display: flex;
    justify-content: space-between;
    gap: 20px;
    padding-top: 14px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 12px;
    color: #7f8b98;
  }
`;

const cards = [
  {
    name: "entre-01-cover",
    body: `
      <div class="eyebrow">ENTREGA CLARA · APPLICATION PROOF</div>
      <div class="split">
        <div>
          <h1>A delivery platform that routes on real streets.</h1>
          <p class="sub">São Paulo food delivery on a real OpenStreetMap graph: time-dependent routing, precedence-aware batching, SSE tracking, and an optional PostgreSQL adapter.</p>
          <div class="metrics">
            <div><b>2,405</b><span>OSM nodes in the product graph</span></div>
            <div><b>291</b><span>backend tests</span></div>
            <div><b>3</b><span>browser journeys with axe</span></div>
          </div>
        </div>
        <div class="visual">
          <img src="${customer}" alt="Customer tracking screen with a deterministic map">
          <div class="caption"><span>Customer tracking</span><span>simulated GPS</span></div>
        </div>
      </div>
      <div class="footer"><span>Simulated payments, GPS and identities</span><span>OSM snapshot · not a live map</span></div>
    `,
  },
  {
    name: "entre-02-evidence",
    body: `
      <div class="eyebrow">MEASURED, NOT ASSERTED</div>
      <h1>85 expansions where Dijkstra needs 53,885.</h1>
      <p class="sub">Contraction hierarchies on a 105k-node city graph: 0.1% of the graph and 2.8 ms per query after a 2.7 s build. Break-even is 12 queries against A*.</p>
      <div class="metrics wide">
        <div><b>53,885 → 85</b><span>median nodes expanded</span></div>
        <div><b>172 → 2.8 ms</b><span>median query time</span></div>
        <div><b>12</b><span>queries to break even vs A*</span></div>
      </div>
      <div class="chart">${tradeoff}</div>
      <div class="footer"><span>City graph · 200 sampled pairs · time objective</span><span>Committed 2026-11-01 run · wall time varies by machine</span></div>
    `,
  },
  {
    name: "entre-03-lab",
    body: `
      <div class="eyebrow">THE INSTRUMENT</div>
      <div class="split">
        <div>
          <h1>One route, two searches, replayed in the browser.</h1>
          <p class="sub">The static lab replays committed traces: ALT finishes in 70 expansions where Dijkstra needs 167, and the day-long ETA curve comes from the committed traffic profile.</p>
          <div class="metrics">
            <div><b>70 vs 167</b><span>ALT vs Dijkstra expansions</span></div>
            <div><b>0</b><span>backend calls in the lab</span></div>
          </div>
        </div>
        <div class="visual">
          <img src="${staticLab}" alt="Static algorithm lab showing the search replay">
          <div class="caption"><span>Static lab</span><span>self-contained replay</span></div>
        </div>
      </div>
      <div class="footer"><span>Replay of committed traces</span><span>No live traffic · API and web shell stay local</span></div>
    `,
  },
];

const browser = await chromium.launch({ channel: "msedge" });
try {
  for (const card of cards) {
    const context = await browser.newContext({
      viewport: { width: 1000, height: 750 },
      deviceScaleFactor: 2,
    });
    const page = await context.newPage();
    await page.setContent(
      `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body><div class="card">${card.body}</div></body></html>`,
      { waitUntil: "load" },
    );
    await page.evaluate(() => document.fonts.ready.then(() => true));
    const layout = await page.evaluate(() => {
      const footer = document.querySelector(".footer");
      const body = document.querySelector(".card");
      const last = footer.previousElementSibling;
      return {
        footerTop: footer.getBoundingClientRect().top,
        lastBottom: last.getBoundingClientRect().bottom,
        scrollHeight: body.scrollHeight,
      };
    });
    if (layout.lastBottom > layout.footerTop || layout.scrollHeight > 750) {
      throw new Error(`${card.name} overflows its card: ${JSON.stringify(layout)}`);
    }
    await page.screenshot({ path: path.join(output, `${card.name}-2x.png`) });
    await context.close();
    console.log(`rendered ${card.name}-2x.png`);
  }
} finally {
  await browser.close();
}
