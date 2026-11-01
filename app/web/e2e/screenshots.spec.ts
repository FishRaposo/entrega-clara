import { test } from "@playwright/test";

// Capture recruiter-facing PNGs into docs/media/. Run the demo scenario to a
// mid-flight state first so each surface shows real data.
test("capturas para documentação", async ({ page }) => {
  await page.goto("/demo");
  const advance = page.getByRole("button", { name: /avançar|replay|executar/i });
  for (let i = 0; i < 8; i += 1) {
    if (!(await advance.first().isVisible().catch(() => false))) break;
    await advance.first().click();
    await page.waitForTimeout(400);
  }

  const shots: Array<[string, string]> = [
    ["/customer", "customer.png"],
    ["/restaurant", "restaurant.png"],
    ["/courier", "courier.png"],
    ["/admin", "operations.png"],
    ["/lab", "lab.png"],
  ];
  for (const [route, name] of shots) {
    await page.goto(route);
    await page.waitForTimeout(800);
    await page.screenshot({
      path: `../../docs/media/${name}`,
      fullPage: false,
    });
  }
});
