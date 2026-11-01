import { expect, test } from "@playwright/test";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

// The static lab is a generated, self-contained page (scripts/media/export_static_lab.py).
// This test proves the baked traces actually execute in a browser: with reduced
// motion the page renders the finished race, so the counters must show the full
// expansion counts of both solvers.
const SITE = resolve(__dirname, "../../../site/index.html");

test("laboratório estático reproduz as traces commitadas", async ({ browser }) => {
  test.skip(!existsSync(SITE), "run `python scripts/media/export_static_lab.py` first");
  const context = await browser.newContext({
    viewport: { width: 1280, height: 1000 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  await page.goto(`file://${SITE.replace(/\\/g, "/")}`);
  await page.waitForTimeout(1200);

  const counters = await page.locator(".counters dd").allTextContents();
  // Dijkstra 167 expansions, ALT 70 — the numbers the page and the README claim.
  expect(counters[0]).toContain("167");
  expect(counters[4]).toContain("70");

  const canvases = page.locator("canvas");
  await expect(canvases).toHaveCount(2);

  await page.screenshot({ path: "../../docs/media/static-lab.png", fullPage: false });
  await context.close();
});
