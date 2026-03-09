"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ActivePipeline, DashboardEvent, PipelineNodeStatus } from "@/types/dashboard";

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL ?? "http://localhost:8080";
const DASHBOARD_API_URL = AGENT_URL.includes("ondigitalocean.app")
  ? `${AGENT_URL}/api`
  : AGENT_URL;
const ACTIVE_POLL_MS = 2_000;
const MAX_EVENTS = 200;

// SSE node name (LangGraph fn) → pipeline-viz node ID
const NODE_NAME_TO_VIZ_ID: Record<string, string> = {
  input_processor: "input",
  cross_examination: "cross_exam",
  strategist_verdict: "verdict",
  decision_gate: "decision",
  doc_generator: "doc_gen",
  code_generator: "code_gen",
  deployer: "deployer",
  feedback_generator: "feedback",
  conditional_review: "review",
};

const AGENT_TO_VIZ_ID: Record<string, string> = {
  architect: "architect",
  scout: "scout",
  catalyst: "catalyst",
  guardian: "guardian",
  advocate: "advocate",
};

// Backend scoring axis → pipeline-viz score node ID
const SCORE_AXIS_TO_VIZ_ID: Record<string, string> = {
  technical_feasibility: "score_tech",
  market_viability: "score_market",
  innovation_score: "score_innovation",
  risk_profile: "score_risk",
  user_impact: "score_user",
};

function resolveVizNodeId(nodeName: string): string | null {
  return NODE_NAME_TO_VIZ_ID[nodeName] ?? null;
}

let _eventSeq = 0;

export function usePipelineMonitor() {
  const [activePipelines, setActivePipelines] = useState<ActivePipeline[]>([]);
  const [events, setEvents] = useState<DashboardEvent[]>([]);
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, PipelineNodeStatus>>({});
  const [connected, setConnected] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const updateNode = useCallback((vizId: string, status: PipelineNodeStatus) => {
    setNodeStatuses((prev) => ({ ...prev, [vizId]: status }));
  }, []);

  const connectSSE = useCallback(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    (async () => {
      try {
        const res = await fetch(`${DASHBOARD_API_URL}/dashboard/events`, {
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

              data._uid = `evt-${++_eventSeq}`;
              data._timestamp = Date.now();
              setEvents((prev) => [data, ...prev].slice(0, MAX_EVENTS));

              if (data.node) {
                const vizId = resolveVizNodeId(data.node);
                if (vizId) {
                  if (data.type.includes(".node.start")) {
                    updateNode(vizId, "active");
                  } else if (data.type.includes(".node.complete")) {
                    updateNode(vizId, "complete");
                  } else if (data.type.includes(".error")) {
                    updateNode(vizId, "error");
                  }
                }

                if (data.node === "run_council_agent") {
                  const status: PipelineNodeStatus = data.type.includes(".node.start") ? "active" : "complete";
                  for (const agentVizId of Object.values(AGENT_TO_VIZ_ID)) {
                    updateNode(agentVizId, status);
                  }
                }

                if (data.node === "score_axis") {
                  const status: PipelineNodeStatus = data.type.includes(".node.start") ? "active" : "complete";
                  for (const scoreVizId of Object.values(SCORE_AXIS_TO_VIZ_ID)) {
                    updateNode(scoreVizId, status);
                  }
                }
              }

              if (data.type === "council.agent.analysis" && data.agent) {
                const agentVizId = AGENT_TO_VIZ_ID[data.agent];
                if (agentVizId) {
                  updateNode(agentVizId, "complete");
                }
              }

              if (data.type === "council.verdict") {
                updateNode("verdict", "complete");
              }

              if (data.type === "deploy.complete") {
                updateNode("deployer", "complete");
              }

              if (data.type === "brainstorm.agent.insight" && data.agent) {
                const agentVizId = AGENT_TO_VIZ_ID[data.agent];
                if (agentVizId) {
                  updateNode(agentVizId, "complete");
                }
              }

              if (data.node === "synthesize_brainstorm") {
                if (data.type.includes(".node.start")) {
                  updateNode("synthesize", "active");
                } else if (data.type.includes(".node.complete")) {
                  updateNode("synthesize", "complete");
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
  }, [updateNode]);

  const fetchActive = useCallback(async () => {
    try {
      const res = await fetch(`${DASHBOARD_API_URL}/dashboard/active`);
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
