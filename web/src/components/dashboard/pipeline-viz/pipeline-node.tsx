"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { CheckCircle, XCircle, Clock, Activity } from "lucide-react";

export type NodeStatus = "idle" | "active" | "complete" | "error";

export interface NodeDef {
  id: string;
  label: string;
  x: number;
  y: number;
  emoji?: string;
  glow?: boolean;
}

export const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

export const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.35, ease: "easeOut" as const } },
};

export function getStatusColor(status: NodeStatus) {
  switch (status) {
    case "active":
      return "border-blue-500 bg-blue-500/20 text-blue-100 shadow-[0_0_22px_rgba(59,130,246,0.32)]";
    case "complete":
      return "border-emerald-500/80 bg-emerald-500/18 text-emerald-100";
    case "error":
      return "border-red-500/80 bg-red-500/18 text-red-100";
    default:
      return "border-slate-600/40 bg-slate-900/55 text-slate-300";
  }
}

export function getStatusIcon(status: NodeStatus) {
  switch (status) {
    case "active":
      return <Activity className="h-3 w-3 animate-pulse" />;
    case "complete":
      return <CheckCircle className="h-3 w-3" />;
    case "error":
      return <XCircle className="h-3 w-3" />;
    default:
      return <Clock className="h-3 w-3 opacity-40" />;
  }
}

interface PipelineNodeProps {
  node: NodeDef;
  status: NodeStatus;
  isOverview: boolean;
  isConditional: boolean;
  meta?: { iteration?: number; maxIterations?: number; repairAttempt?: number; maxRepairs?: number; matchRate?: number; skipped?: boolean };
  topStyle: string;
}

export function PipelineNode({ node, status, isOverview, isConditional, meta, topStyle }: PipelineNodeProps) {
  const shouldGlow = node.glow && (isOverview || status === "active");

  return (
    <motion.div
      variants={fadeUp}
      animate={status === "active" ? { scale: [1, 1.08, 1] } : { scale: 1 }}
      transition={status === "active" ? { repeat: Infinity, duration: 1.8, ease: "easeInOut" } : { duration: 0.3 }}
      className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center"
      style={{ left: `${node.x}%`, top: topStyle }}
    >
      {shouldGlow && (
        <div
          className="glow-ring pointer-events-none absolute inset-0 rounded-full"
          style={{
            boxShadow:
              status === "active"
                ? "0 0 24px 6px rgba(59,130,246,0.36)"
                : node.id === "verified"
                  ? "0 0 18px 4px rgba(16,185,129,0.25)"
                  : "0 0 16px 4px rgba(59,130,246,0.18)",
          }}
        />
      )}
      <div
        className={cn(
          "relative flex items-center gap-1 rounded-full border px-3 py-1.5 text-[11px] font-medium whitespace-nowrap transition-all duration-500 backdrop-blur-sm shadow-[0_6px_18px_rgba(2,6,23,0.28)]",
          getStatusColor(status),
          isOverview && isConditional && "border-dashed opacity-65",
        )}
      >
        {node.emoji ? <span className="text-[11px] leading-none">{node.emoji}</span> : <span>{getStatusIcon(status)}</span>}
        <span>{node.label}</span>
        {status !== "idle" && <span className="ml-0.5">{getStatusIcon(status)}</span>}
        {(() => {
          if (!meta) return null;
          if (meta.skipped) return <span className="ml-1 text-[9px] text-slate-400">(skipped)</span>;
          if (meta.iteration && meta.maxIterations && meta.iteration > 1) {
            return <span className="ml-1 rounded bg-amber-500/25 px-1 text-[9px] font-bold text-amber-300">{meta.iteration}/{meta.maxIterations}</span>;
          }
          if (meta.repairAttempt && meta.maxRepairs) {
            return <span className="ml-1 rounded bg-orange-500/25 px-1 text-[9px] font-bold text-orange-300">fix {meta.repairAttempt}/{meta.maxRepairs}</span>;
          }
          if (meta.matchRate != null && status === "complete") {
            return <span className="ml-1 text-[9px] text-emerald-400">{Math.round(meta.matchRate)}%</span>;
          }
          return null;
        })()}
      </div>
    </motion.div>
  );
}
