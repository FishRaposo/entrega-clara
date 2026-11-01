import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// Full vertical slice: customer → restaurant → courier → delivered.
// Every surface uses its fixed demo identity; the demo never logs in.
test("jornada completa: pedido do cliente até a entrega", async ({ page }) => {
  // 1. Customer: discover, add item, checkout.
  await page.goto("/customer");
  await page.getByRole("button", { name: /Seu Manoel/i }).click();
  await page
    .getByRole("button", { name: /^Adicionar$/ })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Sacola", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /finalizar pedido/i }).click();
  await expect(page.getByRole("heading", { name: /pedido order_/i })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText(/pedido feito/i).first()).toBeVisible();

  // 2. Restaurant: confirm → prepare → ready.
  await page.goto("/restaurant");
  await page.getByRole("button", { name: /confirmar pedido/i }).click();
  await expect(page.getByText(/confirmado/i).first()).toBeVisible();
  await page.getByRole("button", { name: /iniciar preparo/i }).click();
  await expect(page.getByText(/em preparo/i).first()).toBeVisible();
  await page.getByRole("button", { name: /pronto para retirada/i }).click();
  await expect(page.getByText(/aguardando o entregador/i).first()).toBeVisible();

  // 3. Courier: availability → accept → pickup → start → gps ping → complete.
  await page.goto("/courier");
  const goOnline = page.getByRole("button", { name: "Ficar disponível" });
  if (await goOnline.isVisible()) {
    await goOnline.click();
  }
  await page.getByRole("button", { name: /aceitar entrega/i }).click();
  await page.getByRole("button", { name: /retirar no restaurante/i }).click();
  await page.getByRole("button", { name: /iniciar rota/i }).click();
  await page.getByRole("button", { name: /enviar ponto gps/i }).click();
  await page.getByRole("button", { name: /concluir entrega/i }).click();
  await expect(
    page.getByRole("heading", { name: /entrega ativa/i }),
  ).not.toBeVisible();

  // 4. Customer sees the delivered state with tracking + map fallback.
  await page.goto("/customer");
  await expect(page.getByRole("heading", { name: /pedido order_/i })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText(/entregue/i).first()).toBeVisible();

  // 5. Customer rates the delivered order.
  await page.getByRole("button", { name: "5★" }).click();
  await expect(page.getByText(/avaliado/i).first()).toBeVisible();
});

test("laboratório de algoritmos anima a busca sobre ruas reais", async ({
  page,
}) => {
  await page.goto("/lab");
  await expect(
    page.getByRole("heading", { name: /laborat/i }),
  ).toBeVisible();
  // Real street graph loads, then the demo route runs both searches and the
  // canvas reports the work each solver did.
  const canvas = page.locator("canvas").first();
  await expect(canvas).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: /Rota da demo/i }).click();
  await expect(page.getByText(/expandidos/i).first()).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole("button", { name: /Mostrar fim/i })).toBeVisible();
  await expect(page.getByText(/Held-Karp|ótimo/i).first()).toBeVisible({
    timeout: 15_000,
  });
});

test("páginas de papel não têm violações de acessibilidade automáticas", async ({
  page,
}) => {
  for (const route of ["/", "/customer", "/restaurant", "/courier", "/admin", "/demo", "/lab"]) {
    await page.goto(route);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(
      results.violations.map((v) => `${v.id} @ ${route}: ${v.nodes.length} nós`),
    ).toEqual([]);
  }
});
