import { test, type Page } from "@playwright/test";

// Capture recruiter-facing PNGs into docs/media/. The demo scenario is driven in
// three phases so each surface shows real data: kitchen queue, live tracking with
// a route, then the multi-order batch in the courier console.
async function advanceDemo(page: Page, steps: number): Promise<void> {
  const advance = page.getByRole("button", { name: /avançar|replay|executar/i });
  for (let index = 0; index < steps; index += 1) {
    if (!(await advance.first().isVisible().catch(() => false))) break;
    await advance.first().click();
    await page.waitForTimeout(300);
  }
}

async function capture(page: Page, route: string, name: string): Promise<void> {
  await page.goto(route);
  await page.waitForTimeout(800);
  await page.screenshot({ path: `../../docs/media/${name}`, fullPage: false });
}

test("capturas para documentação @screens", async ({ page }) => {
  // Phase 1 — the kitchen queue, before anything is dispatched.
  await page.goto("/demo");
  await advanceDemo(page, 8);
  await capture(page, "/restaurant", "restaurant.png");

  // Phase 2 — courier en route: the customer view has a route and live points.
  await page.goto("/demo");
  await advanceDemo(page, 7);
  await capture(page, "/customer", "customer.png");

  // Phase 3 — past the batch-accept step (28): courier tour + operations timeline.
  await page.goto("/demo");
  await advanceDemo(page, 17);
  await capture(page, "/courier", "courier.png");
  await capture(page, "/admin", "operations.png");

  // The lab runs the delivery route so the capture shows two finished searches
  // on real streets rather than an empty graph.
  await page.goto("/lab");
  const demo = page.getByRole("button", { name: /Rota da demo/i });
  await demo.waitFor({ timeout: 20_000 });
  await demo.click();
  await page.waitForTimeout(2_500);
  await page.locator(".lab-counters").first().scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await page.screenshot({ path: "../../docs/media/lab.png", fullPage: false });
});
