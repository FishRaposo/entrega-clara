import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { DemoStatusCard } from "../../app/web/src/components/demo-status-card";

const snapshot = (overrides: Record<string, unknown> = {}) => ({
  scenario_id: "lunch-rush",
  description: "Demo",
  clock: "2026-09-01T12:00:00+00:00",
  run_id: 0,
  step_index: 1,
  steps_total: 10,
  remaining_steps: 9,
  order: { id: "ord-demo-001", state: "placed", total_minor: 4290 },
  delivery: null,
  route: null,
  tracking_points: 0,
  notifications: [],
  ...overrides,
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("demo controls inspect and mutate the backend scenario through the proxy", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => snapshot() })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => snapshot({ step_index: 2, order: { id: "ord-demo-001", state: "confirmed", total_minor: 4290 } }),
    });
  vi.stubGlobal("fetch", fetchMock);

  render(<DemoStatusCard locationLabel="Área central de São Paulo, SP" />);

  await screen.findByText(/pedido #ord-demo-001/i);
  fireEvent.click(screen.getByRole("button", { name: /avançar passo/i }));

  await screen.findByText(/confirmado/i);
  await waitFor(() => {
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/demo/advance",
      expect.objectContaining({ method: "POST", body: '{"event_count":1}' }),
    );
  });
});

test("advance button disables when the script is exhausted", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => snapshot({ step_index: 10, remaining_steps: 0 }),
    }),
  );

  render(<DemoStatusCard locationLabel="Área central de São Paulo, SP" />);

  const button = await screen.findByRole("button", { name: /avançar passo/i });
  await waitFor(() => expect(button).toBeDisabled());
});
