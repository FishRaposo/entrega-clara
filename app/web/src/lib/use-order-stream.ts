"use client";

import { useEffect, useRef, useState } from "react";

import type { DomainEvent, Order } from "./api-types";
import type { DemoIdentity } from "./identities";

type StreamState = {
  snapshot: Order | null;
  events: DomainEvent[];
  connected: boolean;
};

/**
 * Fetch-based SSE reader — EventSource cannot send the X-Demo-Identity
 * header, so we parse the event-stream ourselves. Emits the initial
 * `snapshot` event then appends every domain event for the order.
 */
export function useOrderStream(identity: DemoIdentity, orderId: string | null): StreamState {
  const [state, setState] = useState<StreamState>({
    snapshot: null,
    events: [],
    connected: false,
  });
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!orderId) {
      setState({ snapshot: null, events: [], connected: false });
      return;
    }
    const abort = new AbortController();
    abortRef.current = abort;
    setState({ snapshot: null, events: [], connected: false });

    const run = async () => {
      try {
        const response = await fetch(`/api/v1/orders/${orderId}/stream`, {
          headers: { "x-demo-identity": identity },
          signal: abort.signal,
        });
        if (!response.ok || !response.body) return;
        setState((s) => ({ ...s, connected: true }));
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";
          for (const frame of frames) {
            const dataLines = frame
              .split("\n")
              .filter((line) => line.startsWith("data:"))
              .map((line) => line.slice(5).trim());
            if (dataLines.length === 0) continue;
            const eventName =
              frame
                .split("\n")
                .find((line) => line.startsWith("event:"))
                ?.slice(6)
                .trim() ?? "message";
            const parsed = JSON.parse(dataLines.join("\n")) as unknown;
            setState((s) =>
              eventName === "snapshot"
                ? { ...s, snapshot: parsed as Order }
                : { ...s, events: [...s.events, parsed as DomainEvent] },
            );
          }
        }
      } catch {
        // aborted or network loss — stream ends silently for the demo
      } finally {
        setState((s) => ({ ...s, connected: false }));
      }
    };
    void run();
    return () => abort.abort();
  }, [identity, orderId]);

  return state;
}
