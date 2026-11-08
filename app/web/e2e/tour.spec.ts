import { test } from "@playwright/test";
import { resolve } from "node:path";

// Records the reviewer-facing tour into docs/media/demo-tour.webm: the demo
// scenario advanced to the courier batch, the console with its planned stops,
// the customer tracking view and the lab race. It writes a tracked file, so it
// is opt-in:
//   TOUR=1 npx playwright test e2e/tour.spec.ts
test.skip(!process.env.TOUR, "set TOUR=1 to record the tour");
test.use({ video: { mode: "on", size: { width: 1280, height: 720 } } });

test("tour gravado: demo, console, rastreio e laboratório", async ({ page }) => {
  const video = page.video();

  await page.goto("/");
  await page.waitForTimeout(1_500);
  await page.goto("/demo");
  await page.waitForTimeout(1_000);

  const advance = page.getByRole("button", { name: /avançar|replay|executar/i });
  for (let step = 0; step < 22; step += 1) {
    if (!(await advance.first().isVisible().catch(() => false))) break;
    await advance.first().click();
    await page.waitForTimeout(420);
  }

  await page.goto("/courier");
  await page.waitForTimeout(2_800);
  await page.goto("/customer");
  await page.waitForTimeout(2_500);

  await page.goto("/lab");
  const demo = page.getByRole("button", { name: /Rota da demo/i });
  await demo.waitFor({ timeout: 20_000 });
  await demo.click();
  await page.waitForTimeout(3_000);
  await page.locator(".traffic-strip").scrollIntoViewIfNeeded();
  await page.waitForTimeout(2_500);

  await page.close();
  if (video) {
    await video.saveAs(resolve(__dirname, "../../../docs/media/demo-tour.webm"));
  }
});
