export type HealthResponse = {
  status: string;
};

export type DemoScenario = {
  scenario_id: string;
  clock_minutes: number;
  active_order: {
    id: string;
    state: string;
  };
};

export type DemoMutation = {
  scenario_id: string;
  clock_minutes: number;
  active_order: {
    id: string;
    state: string;
  };
};

type RequestOptions = Omit<RequestInit, "body"> & { body?: unknown };

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      "content-type": "application/json",
      ...options.headers,
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (!response.ok) {
    throw new Error(`Demo API request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/v1/health");
}

export function getDemoScenario(): Promise<DemoScenario> {
  return request<DemoScenario>("/api/v1/demo/scenario");
}

export function resetDemo(): Promise<DemoMutation> {
  return request<DemoMutation>("/api/v1/demo/reset", { method: "POST" });
}

export function advanceDemo(eventCount: number): Promise<DemoMutation> {
  return request<DemoMutation>("/api/v1/demo/advance", {
    method: "POST",
    body: { event_count: eventCount },
  });
}
