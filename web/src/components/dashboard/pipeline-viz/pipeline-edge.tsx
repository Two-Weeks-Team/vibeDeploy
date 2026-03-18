"use client";

import { cn } from "@/lib/utils";
import { NodeDef, NodeStatus } from "./pipeline-node";

export interface EdgeDef {
  source: string;
  target: string;
}

export const EDGE_COLORS: Record<NodeStatus, string> = {
  idle: "rgba(148,163,184,0.35)",
  active: "rgba(59,130,246,0.82)",
  complete: "rgba(16,185,129,0.65)",
  error: "rgba(239,68,68,0.65)",
};

export const SVG_STYLES = `
  @keyframes edgeFlow {
    to { stroke-dashoffset: -16; }
  }
  @keyframes edgeFlowFast {
    to { stroke-dashoffset: -16; }
  }
  @keyframes glowPulse {
    0%, 100% { opacity: 0.12; }
    50% { opacity: 0.45; }
  }
  .edge-idle {
    stroke-dasharray: 5 3;
    animation: edgeFlow 2.5s linear infinite;
  }
  .edge-active {
    stroke-dasharray: 8 3;
    animation: edgeFlowFast 0.6s linear infinite;
  }
  .edge-complete {
    stroke-dasharray: none;
  }
  .glow-ring {
    animation: glowPulse 3s ease-in-out infinite;
  }
`;

export function buildEdgeCurve(source: NodeDef, target: NodeDef, includeMove: boolean) {
  const midY = (source.y + target.y) / 2;
  const command = `C ${source.x} ${midY}, ${target.x} ${midY}, ${target.x} ${target.y}`;
  return includeMove ? `M ${source.x} ${source.y} ${command}` : command;
}

interface PipelineEdgeProps {
  edge: EdgeDef;
  sourceNode: NodeDef;
  targetNode: NodeDef;
  sourceStatus: NodeStatus;
  targetStatus: NodeStatus;
}

export function PipelineEdge({ edge, sourceNode, targetNode, sourceStatus, targetStatus }: PipelineEdgeProps) {
  let stroke = EDGE_COLORS.idle;
  let edgeClass = "edge-idle";
  let marker = "arr-idle";
  let showGlow = false;

  if (sourceStatus === "complete" && (targetStatus === "active" || targetStatus === "complete")) {
    stroke = EDGE_COLORS.active;
    edgeClass = "edge-active";
    marker = "arr-active";
    showGlow = true;
  } else if (sourceStatus === "complete") {
    stroke = EDGE_COLORS.complete;
    edgeClass = "edge-complete";
    marker = "arr-complete";
  } else if (sourceStatus === "error" || targetStatus === "error") {
    stroke = EDGE_COLORS.error;
    edgeClass = "edge-complete";
  }

  const d = buildEdgeCurve(sourceNode, targetNode, true);

  return (
    <g>
      {showGlow && (
        <path
          d={d}
          fill="none"
          stroke={stroke}
          strokeWidth={3.8}
          filter="url(#edge-glow)"
          opacity={0.3}
          vectorEffect="non-scaling-stroke"
        />
      )}
      <path
        d={d}
        fill="none"
        stroke={stroke}
        strokeWidth={1.4}
        markerEnd={`url(#${marker})`}
        vectorEffect="non-scaling-stroke"
        className={cn(edgeClass, "transition-colors duration-300")}
      />
    </g>
  );
}
