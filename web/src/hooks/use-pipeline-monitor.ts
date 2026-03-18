"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ActivePipeline, DashboardEvent, NodeMetadata, PipelineNodeStatus } from "@/types/dashboard";

import { DASHBOARD_API_URL } from "@/lib/api";
import { createSSEClient } from "@/lib/sse-client";

const ACTIVE_POLL_MS = 30_000;
const MAX_EVENTS = 200;

const NODE_NAME_TO_VIZ_ID: Record<string, string> = {
  input_processor: "input",
  enrich_idea: "enrich",
  cross_examination: "cross_exam",
  strategist_verdict: "verdict",
  decision_gate: "decision",
  fix_storm: "fix_storm",
  scope_down: "scope_down",
  doc_generator: "doc_gen",
  blueprint_generator: "blueprint",
  prompt_strategist: "prompt_strategy",
  code_generator: "code_gen",
  code_evaluator: "code_eval",
  build_validator: "build_validate",
};

const AGENT_TO_VIZ_ID: Record<string, string> = {
  architect: "architect",
  scout: "scout",
  catalyst: "catalyst",
  guardian: "guardian",
  advocate: "advocate",
};

const SCORE_AXIS_TO_VIZ_ID: Record<string, string> = {
  technical_feasibility: "score_tech",
  market_viability: "score_market",
  innovation_score: "score_innovation",
  risk_profile: "score_risk",
  user_impact: "score_user",
};
const DIRECT_VIZ_NODE_IDS = new Set([
  "architect",
  "scout",
  "catalyst",
  "guardian",
  "advocate",
  "score_tech",
  "score_market",
  "score_innovation",
  "score_risk",
  "score_user",
  "build_validate",
  "git_push",
  "ci_test",
  "app_spec",
  "do_build",
  "do_deploy",
  "verified",
  "prompt_strategy",
  "blueprint",
  "code_gen",
  "code_eval",
]);

function resolveVizNodeId(nodeName: string): string | null {
  return NODE_NAME_TO_VIZ_ID[nodeName] ?? (DIRECT_VIZ_NODE_IDS.has(nodeName) ? nodeName : null);
}

let _eventSeq = 0;

export function usePipelineMonitor() {
  const [activePipelines, setActivePipelines] = useState<ActivePipeline[]>([]);
  const [events, setEvents] = useState<DashboardEvent[]>([]);
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, PipelineNodeStatus>>({});
  const [nodeMetadata, setNodeMetadata] = useState<Record<string, NodeMetadata>>({});
  const [connected, setConnected] = useState(false);
  const abortRef = useRef<(() => void) | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevPipelineIds = useRef<Set<string>>(new Set());
  const clearTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const updateNode = useCallback((vizId: string, status: PipelineNodeStatus) => {
    setNodeStatuses((prev: Record<string, PipelineNodeStatus>) => ({ ...prev, [vizId]: status }));
  }, []);

  const updateMetadata = useCallback((vizId: string, meta: Partial<NodeMetadata>) => {
    setNodeMetadata((prev) => ({
      ...prev,
      [vizId]: { ...prev[vizId], ...meta },
    }));
  }, []);

  const connectSSE = useCallback(() => {
    abortRef.current?.();
    setConnected(true);

    const abort = createSSEClient({
      url: `${DASHBOARD_API_URL}/dashboard/events`,
      body: {},
      onEvent: (sseEvent) => {
        try {
          const data = sseEvent.data as unknown as DashboardEvent;
          if (data.type === "heartbeat") return;

          if (data.type === "active_pipelines") {
            const pipelines = Array.isArray(data.pipelines)
              ? (data.pipelines as ActivePipeline[])
              : [];
            const currentIds = new Set(pipelines.map((p) => p.thread_id));
            const hadPipelines = prevPipelineIds.current.size > 0;
            const nowEmpty = currentIds.size === 0;

            if (hadPipelines && nowEmpty) {
              if (clearTimer.current) clearTimeout(clearTimer.current);
              clearTimer.current = setTimeout(() => {
                setNodeStatuses({});
                setNodeMetadata({});
              }, 2000);
            } else if (!nowEmpty && clearTimer.current) {
              clearTimeout(clearTimer.current);
              clearTimer.current = null;
            }

            prevPipelineIds.current = currentIds;
            setActivePipelines(pipelines);
            return;
          }

          data._uid = `evt-${++_eventSeq}`;
          data._timestamp = Date.now();
          setEvents((prev: DashboardEvent[]) => [data, ...prev].slice(0, MAX_EVENTS));

          if (data.node) {
            const vizId = resolveVizNodeId(String(data.node));
            if (vizId) {
              if (data.type.includes(".node.start")) {
                updateNode(vizId, "active");
              } else if (data.type.includes(".node.complete")) {
                updateNode(vizId, "complete");
              } else if (data.type === "council.agent.analysis" || data.type === "scoring.axis.complete") {
                updateNode(vizId, "complete");
              } else if (data.type.includes(".start")) {
                updateNode(vizId, "active");
              } else if (data.type.includes(".complete")) {
                updateNode(vizId, "complete");
              } else if (data.type.includes(".error")) {
                updateNode(vizId, "error");
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

          if (data.type === "scoring.axis.complete" && data.axis) {
            const scoreVizId = SCORE_AXIS_TO_VIZ_ID[String(data.axis)];
            if (scoreVizId) {
              updateNode(scoreVizId, "complete");
            }
          }

          if (data.type === "deploy.complete") {
            updateNode("do_deploy", "complete");
            // Do not force verified — let the actual verified event determine its status
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

          if (data.type === "blueprint.complete") {
            updateNode("blueprint", "complete");
          }

          if (data.type === "code_gen.complete") {
            updateNode("code_gen", "complete");
          }

          if (data.type === "code_eval.result") {
            updateNode("code_eval", data.passed ? "complete" : "active");
            updateMetadata("code_eval", {
              passed: Boolean(data.passed),
              iteration: Number(data.iteration) || undefined,
              maxIterations: Number(data.max_iterations) || undefined,
              matchRate: Number(data.match_rate) || undefined,
              completeness: Number(data.completeness) || undefined,
              consistency: Number(data.consistency) || undefined,
              runnability: Number(data.runnability) || undefined,
              experience: Number(data.experience) || undefined,
              blockers: Array.isArray(data.blockers) ? data.blockers as string[] : undefined,
            });
          }

          if (data.type === "build.node.complete" || data.type === "build.node.error") {
            updateMetadata("build_validate", {
              passed: Boolean(data.passed),
              skipped: Boolean(data.skipped),
              backendOk: data.backend_ok != null ? Boolean(data.backend_ok) : undefined,
              frontendOk: data.frontend_ok != null ? Boolean(data.frontend_ok) : undefined,
            });
          }

          if (data.type?.startsWith("deploy.") && data.ci_repair_attempt != null) {
            updateMetadata("ci_test", {
              repairAttempt: Number(data.ci_repair_attempt),
              maxRepairs: Number(data.max_retries) || 3,
            });
          }

          if (data.type?.startsWith("deploy.") && data.deploy_repair_attempt != null) {
            updateMetadata("do_build", {
              repairAttempt: Number(data.deploy_repair_attempt),
              maxRepairs: 3,
            });
          }
        } catch { }
      },
      onComplete: () => {
        setConnected(false);
      },
      onError: () => {
        setConnected(false);
        reconnectTimer.current = setTimeout(connectSSE, 3_000);
      },
    });

    abortRef.current = abort;
  }, [updateNode, updateMetadata]);

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
      abortRef.current?.();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (clearTimer.current) clearTimeout(clearTimer.current);
      clearInterval(id);
    };
  }, [connectSSE, fetchActive]);

  return {
    activePipelines,
    events,
    nodeStatuses,
    nodeMetadata,
    connected,
  };
}
