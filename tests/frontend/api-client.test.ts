import { afterEach, expect, test, vi } from "vitest";

import { getDemoScenario, resetDemo } from "../../app/web/src/lib/api-client";

const scenario = {
  scenario_id: "lunch-rush",
  clock_minutes: 0,
  active_order: { id: "demo-order-001", state: "placed" },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

test("browser API requests use the same-origin proxy path", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => scenario,
  });
  vi.stubGlobal("fetch", fetchMock);

  await getDemoScenario();
  await resetDemo();

  expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/v1/demo/scenario", expect.any(Object));
  expect(fetchMock).toHaveBeenNthCalledWith(
    2,
    "/api/v1/demo/reset",
    expect.objectContaining({ method: "POST" }),
  );
});
