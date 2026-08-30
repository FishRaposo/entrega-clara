import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { DemoStatusCard } from "../../app/web/src/components/demo-status-card";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("demo controls inspect and mutate the backend scenario through the proxy", async () => {
  const initial = {
    scenario_id: "lunch-rush",
    clock_minutes: 0,
    active_order: { id: "demo-order-001", state: "placed" },
  };
  const advanced = {
    ...initial,
    clock_minutes: 1,
    active_order: { ...initial.active_order, state: "confirmed" },
  };
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => initial })
    .mockResolvedValueOnce({ ok: true, json: async () => advanced });
  vi.stubGlobal("fetch", fetchMock);

  render(<DemoStatusCard locationLabel="Área central de São Paulo, SP" />);

  await screen.findByText(/pedido #demo-order-001/i);
  fireEvent.click(screen.getByRole("button", { name: /avançar cenário/i }));

  await screen.findByText(/confirmado/i);
  await waitFor(() => {
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/demo/advance",
      expect.objectContaining({ method: "POST", body: '{"event_count":1}' }),
    );
  });
});
