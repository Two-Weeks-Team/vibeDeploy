"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getBuildEventsUrl } from "@/lib/zero-prompt-api";
import type { NodeMetadata, PipelineNodeStatus } from "@/types/dashboard";

const NODE_NAME_TO_VIZ_ID: Record<string, string> = {
  input_processor: "input",
  enrich_idea: "enrich",
  doc_generator: "doc_gen",
  blueprint_generator: "blueprint",
  prompt_strategist: "prompt_strategy",
  code_generator: "code_gen",
  code_evaluator: "code_eval",
  build_validator: "build_validate",
};

const DIRECT_VIZ_NODE_IDS = new Set([
  "blueprint", "prompt_strategy", "build_validate",
  "git_push", "ci_test", "app_spec", "do_build", "do_deploy", "verified",
]);

function resolveVizNodeId(nodeName: string): string | null {
  if (DIRECT_VIZ_NODE_IDS.has(nodeName)) return nodeName;
  return NODE_NAME_TO_VIZ_ID[nodeName] ?? null;
}

interface BuildMonitorState {
  nodeStatuses: Record<string, PipelineNodeStatus>;
  nodeMetadata: Record<string, NodeMetadata>;
  currentPhase: string;
  currentNode: string;
  isDone: boolean;
  finalStatus: string | null;
}

export function useBuildMonitor(sessionId: string | null, cardId: string | null) {
  const [state, setState] = useState<BuildMonitorState>({
    nodeStatuses: {},
    nodeMetadata: {},
    currentPhase: "",
    currentNode: "",
    isDone: false,
    finalStatus: null,
  });
  const eventSourceRef = useRef<EventSource | null>(null);

  const updateNode = useCallback((vizId: string, status: PipelineNodeStatus) => {
    setState((prev) => ({
      ...prev,
      nodeStatuses: { ...prev.nodeStatuses, [vizId]: status },
    }));
  }, []);

  const updateMetadata = useCallback((vizId: string, meta: Partial<NodeMetadata>) => {
    setState((prev) => ({
      ...prev,
      nodeMetadata: {
        ...prev.nodeMetadata,
        [vizId]: { ...prev.nodeMetadata[vizId], ...meta },
      },
    }));
  }, []);

  useEffect(() => {
    if (!sessionId || !cardId) return;

    const url = getBuildEventsUrl(sessionId, cardId);
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "keepalive") return;

        if (data.type === "zp.build.done") {
          setState((prev) => ({ ...prev, isDone: true, finalStatus: data.status || "deployed" }));
          es.close();
          return;
        }

        if (data.phase) {
          setState((prev) => ({ ...prev, currentPhase: data.phase }));
        }
        if (data.node || data.stage) {
          setState((prev) => ({ ...prev, currentNode: data.node || data.stage || "" }));
        }

        const nodeName = data.node || data.stage || "";
        const vizId = resolveVizNodeId(nodeName);

        if (vizId) {
          const eventType = String(data.type || "");
          if (eventType.includes("start")) {
            updateNode(vizId, "active");
          } else if (eventType.includes("complete") || eventType.includes("done")) {
            updateNode(vizId, "complete");
          } else if (eventType.includes("error") || eventType.includes("fail")) {
            updateNode(vizId, "error");
          }
        }

        if (data.type === "code_eval.result") {
          updateNode("code_eval", data.passed ? "complete" : "active");
          updateMetadata("code_eval", {
            passed: Boolean(data.passed),
            iteration: Number(data.iteration) || undefined,
            maxIterations: Number(data.max_iterations) || undefined,
            matchRate: Number(data.match_rate) || undefined,
          });
        }

        if (data.type === "build.node.complete" || data.type === "build.node.error") {
          updateMetadata("build_validate", {
            passed: Boolean(data.passed),
            skipped: Boolean(data.skipped),
          });
        }

        if (data.ci_repair_attempt != null) {
          updateMetadata("ci_test", {
            repairAttempt: Number(data.ci_repair_attempt),
            maxRepairs: Number(data.max_retries) || 3,
          });
        }
        if (data.deploy_repair_attempt != null) {
          updateMetadata("do_build", {
            repairAttempt: Number(data.deploy_repair_attempt),
            maxRepairs: 3,
          });
        }

        if (data.type?.startsWith("deploy.step.")) {
          const deployNode = data.node || data.stage;
          if (deployNode && DIRECT_VIZ_NODE_IDS.has(deployNode)) {
            if (data.type.includes("start")) {
              updateNode(deployNode, "active");
            } else if (data.type.includes("complete")) {
              updateNode(deployNode, "complete");
            }
          }
        }
      } catch (err) {
        if (process.env.NODE_ENV === "development") {
          console.warn("[useBuildMonitor] Failed to parse SSE event:", err);
        }
      }
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [sessionId, cardId, updateNode, updateMetadata]);

  return state;
}
