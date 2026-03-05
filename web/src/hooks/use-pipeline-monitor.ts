"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ActivePipeline, DashboardEvent, PipelineNodeStatus } from "@/types/dashboard";

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL ?? "http://localhost:8080";
const ACTIVE_POLL_MS = 2_000;
const MAX_EVENTS = 200;

export function usePipelineMonitor() {
  const [activePipelines, setActivePipelines] = useState<ActivePipeline[]>([]);
  const [events, setEvents] = useState<DashboardEvent[]>([]);
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, PipelineNodeStatus>>({});
  const [connected, setConnected] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connectSSE = useCallback(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    (async () => {
      try {
        const res = await fetch(`${AGENT_URL}/dashboard/events`, {
          signal: controller.signal,
        });
        if (!res.ok || !res.body) throw new Error("SSE connect failed");

        setConnected(true);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith(":")) continue;
            if (!trimmed.startsWith("data: ")) continue;

            try {
              const data: DashboardEvent = JSON.parse(trimmed.slice(6));
              if (data.type === "heartbeat") continue;

              setEvents((prev) => [data, ...prev].slice(0, MAX_EVENTS));

              if (data.node) {
                if (data.type.includes(".node.start")) {
                  setNodeStatuses((prev) => ({ ...prev, [data.node!]: "active" }));
                } else if (data.type.includes(".node.complete")) {
                  setNodeStatuses((prev) => ({ ...prev, [data.node!]: "complete" }));
                } else if (data.type.includes(".error")) {
                  setNodeStatuses((prev) => ({ ...prev, [data.node!]: "error" }));
                }
              }

              if (data.type.includes(".phase.complete") || data.type.includes(".error")) {
                setNodeStatuses({});
              }
            } catch { }
          }
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setConnected(false);
        reconnectTimer.current = setTimeout(connectSSE, 3_000);
      }
    })();
  }, []);

  const fetchActive = useCallback(async () => {
    try {
      const res = await fetch(`${AGENT_URL}/dashboard/active`);
      if (res.ok) setActivePipelines(await res.json());
    } catch { }
  }, []);

  useEffect(() => {
    connectSSE();
    fetchActive();
    const id = setInterval(fetchActive, ACTIVE_POLL_MS);

    return () => {
      abortRef.current?.abort();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      clearInterval(id);
    };
  }, [connectSSE, fetchActive]);

  return {
    activePipelines,
    events,
    nodeStatuses,
    connected,
  };
}
