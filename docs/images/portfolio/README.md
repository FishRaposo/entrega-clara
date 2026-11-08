# Portfolio images

Three 1000×750 cards for Entrega Clara, rendered from the repository's own captures and committed
benchmark — not redrawn, not mocked.

| File | What it shows | Source |
| --- | --- | --- |
| `entre-01-cover.png` | Customer tracking on the real OSM graph, with the platform thesis and the current test counts | `docs/media/customer.png` |
| `entre-02-evidence.png` | The measured city ladder: 53,885 → 85 expansions, 172 → 2.8 ms, break-even 12 queries | `docs/benchmarks/routing-city-tradeoff.svg` |
| `entre-03-lab.png` | The static lab replaying ALT 70 vs Dijkstra 167 | `docs/media/static-lab.png` |

**How they were made.** `app/web/scripts/build-portfolio-cards.mjs` renders each layout with
Playwright at `deviceScaleFactor: 2` (2000×1500) and refuses to save a card whose content overlaps
its footer. `docs/images/portfolio/downscale.py` resizes the renders to exactly **1000×750** with
Lanczos resampling and removes the intermediates. From `app/web`:

```bash
node scripts/build-portfolio-cards.mjs
python ../../docs/images/portfolio/downscale.py   # requires Pillow
```

The arithmetic is fixed: 1000×750 card at 2× = 2000×1500, then a single Lanczos resize to 1000×750.

**What the cards claim, and what they do not.**

- **Cover:** the counts are the 2026-11-08 gate — 291 backend, 19 frontend, 3 browser journeys. The
  screens are demo mode with seeded data; payments, GPS and identities are simulated.
- **Evidence:** the city benchmark is the committed 2026-11-01 run on the OSM extract; wall time
  varies by machine, and the machine is recorded in the artifact. The chart is the repository's own
  generated SVG.
- **Lab:** the static lab replays committed traces. It makes no backend calls, shows no live traffic,
  and is not a deployed version of the product.

**Provenance.** The street graph is a dated OpenStreetMap snapshot (ODbL), not a live map. The
screenshots come from the running app in deterministic demo mode; the limits in the card footers are
part of the image.
