"use client";

import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { AGENT_MAP } from "@/config/agents";
import { PipelineNode, NodeStatus, NodeDef, containerVariants } from "./pipeline-node";
import { PipelineEdge, EdgeDef, EDGE_COLORS, SVG_STYLES } from "./pipeline-edge";
import { ParticleLayer } from "./particle-layer";

export type PipelineType = "evaluation" | "brainstorm";

export interface PhaseLabel {
  label: string;
  y: number;
  color: string;
}

export interface CalloutDef {
  label: string;
  x: number;
  y: number;
  className: string;
}

export const SVG_WIDTH = 100;
export const SVG_HEIGHT = 92;

export function toVerticalPercent(y: number) {
  return `${(y / SVG_HEIGHT) * 100}%`;
}

export const evalNodes: NodeDef[] = [
  { id: "input", label: "Input Processor", x: 50, y: 4, emoji: "📝" },
  { id: "enrich", label: "Enrich Idea", x: 50, y: 11, emoji: "✨" },
  { id: "architect", label: "Architect", x: 10, y: 20, emoji: AGENT_MAP.architect.emoji },
  { id: "scout", label: "Scout", x: 30, y: 20, emoji: AGENT_MAP.scout.emoji },
  { id: "catalyst", label: "Catalyst", x: 50, y: 20, emoji: AGENT_MAP.catalyst.emoji },
  { id: "guardian", label: "Guardian", x: 70, y: 20, emoji: AGENT_MAP.guardian.emoji },
  { id: "advocate", label: "Advocate", x: 90, y: 20, emoji: AGENT_MAP.advocate.emoji },
  { id: "cross_exam", label: "Cross Examination", x: 50, y: 29, emoji: "⚔️" },
  { id: "score_tech", label: "Tech Feasibility", x: 10, y: 38, emoji: "📊" },
  { id: "score_market", label: "Market Viability", x: 30, y: 38, emoji: "📊" },
  { id: "score_innovation", label: "Innovation Score", x: 50, y: 38, emoji: "📊" },
  { id: "score_risk", label: "Risk Profile", x: 70, y: 38, emoji: "📊" },
  { id: "score_user", label: "User Impact", x: 90, y: 38, emoji: "📊" },
  { id: "verdict", label: "Strategist Verdict", x: 50, y: 47, emoji: AGENT_MAP.strategist.emoji, glow: true },
  { id: "decision", label: "Decision Gate", x: 50, y: 53, emoji: "🚦" },
  { id: "fix_storm", label: "Fix Storm", x: 22, y: 60, emoji: "🔧" },
  { id: "scope_down", label: "Scope Down", x: 70, y: 60, emoji: "📐" },
  { id: "doc_gen", label: "Doc Generator", x: 18, y: 68, emoji: "📄" },
  { id: "blueprint", label: "Blueprint Generator", x: 44, y: 68, emoji: "🗺️" },
  { id: "prompt_strategy", label: "Prompt Strategist", x: 62, y: 68, emoji: "🧭" },
  { id: "code_gen", label: "Code Generator", x: 80, y: 68, emoji: "💻" },
  { id: "code_eval", label: "Code Evaluator", x: 50, y: 76, emoji: "✅" },
  { id: "build_validate", label: "Build Validate", x: 50, y: 81, emoji: "🔨" },
  { id: "git_push", label: "Git Push", x: 8, y: 86, emoji: "📦" },
  { id: "ci_test", label: "CI Test", x: 24, y: 86, emoji: "⚙️" },
  { id: "app_spec", label: "App Spec", x: 40, y: 86, emoji: "📋" },
  { id: "do_build", label: "Build", x: 56, y: 86, emoji: "🏗️" },
  { id: "do_deploy", label: "Deploy", x: 72, y: 86, emoji: "🚀" },
  { id: "verified", label: "Verified Live", x: 88, y: 86, emoji: "✅", glow: true },
];

export const evalEdges: EdgeDef[] = [
  { source: "input", target: "enrich" },
  { source: "enrich", target: "architect" },
  { source: "enrich", target: "scout" },
  { source: "enrich", target: "catalyst" },
  { source: "enrich", target: "guardian" },
  { source: "enrich", target: "advocate" },
  { source: "architect", target: "cross_exam" },
  { source: "scout", target: "cross_exam" },
  { source: "catalyst", target: "cross_exam" },
  { source: "guardian", target: "cross_exam" },
  { source: "advocate", target: "cross_exam" },
  { source: "cross_exam", target: "score_tech" },
  { source: "cross_exam", target: "score_market" },
  { source: "cross_exam", target: "score_innovation" },
  { source: "cross_exam", target: "score_risk" },
  { source: "cross_exam", target: "score_user" },
  { source: "score_tech", target: "verdict" },
  { source: "score_market", target: "verdict" },
  { source: "score_innovation", target: "verdict" },
  { source: "score_risk", target: "verdict" },
  { source: "score_user", target: "verdict" },
  { source: "verdict", target: "decision" },
  { source: "decision", target: "doc_gen" },
  { source: "decision", target: "fix_storm" },
  { source: "decision", target: "scope_down" },
  { source: "fix_storm", target: "architect" },
  { source: "fix_storm", target: "scout" },
  { source: "fix_storm", target: "catalyst" },
  { source: "fix_storm", target: "guardian" },
  { source: "fix_storm", target: "advocate" },
  { source: "scope_down", target: "doc_gen" },
  { source: "doc_gen", target: "blueprint" },
  { source: "blueprint", target: "prompt_strategy" },
  { source: "prompt_strategy", target: "code_gen" },
  { source: "code_gen", target: "code_eval" },
  { source: "code_eval", target: "build_validate" },
  { source: "build_validate", target: "git_push" },
  { source: "code_eval", target: "code_gen" },
  { source: "git_push", target: "ci_test" },
  { source: "ci_test", target: "app_spec" },
  { source: "app_spec", target: "do_build" },
  { source: "do_build", target: "do_deploy" },
  { source: "do_deploy", target: "verified" },
];

export const brainstormNodes: NodeDef[] = [
  { id: "input", label: "Input", x: 50, y: 10, emoji: "📝" },
  { id: "architect", label: "Architect", x: 10, y: 45, emoji: AGENT_MAP.architect.emoji },
  { id: "scout", label: "Scout", x: 30, y: 45, emoji: AGENT_MAP.scout.emoji },
  { id: "catalyst", label: "Catalyst", x: 50, y: 45, emoji: AGENT_MAP.catalyst.emoji },
  { id: "guardian", label: "Guardian", x: 70, y: 45, emoji: AGENT_MAP.guardian.emoji },
  { id: "advocate", label: "Advocate", x: 90, y: 45, emoji: AGENT_MAP.advocate.emoji },
  { id: "synthesize", label: "Synthesize", x: 50, y: 85, emoji: AGENT_MAP.strategist.emoji, glow: true },
];

export const brainstormEdges: EdgeDef[] = [
  { source: "input", target: "architect" },
  { source: "input", target: "scout" },
  { source: "input", target: "catalyst" },
  { source: "input", target: "guardian" },
  { source: "input", target: "advocate" },
  { source: "architect", target: "synthesize" },
  { source: "scout", target: "synthesize" },
  { source: "catalyst", target: "synthesize" },
  { source: "guardian", target: "synthesize" },
  { source: "advocate", target: "synthesize" },
];

export const evalPhaseLabels: PhaseLabel[] = [
  { label: "INPUT", y: 3, color: "text-slate-500" },
  { label: "ENRICH", y: 10, color: "text-slate-500" },
  { label: "COUNCIL", y: 19, color: "text-slate-500" },
  { label: "DEBATE", y: 28, color: "text-slate-500" },
  { label: "SCORING", y: 37, color: "text-slate-500" },
  { label: "VERDICT", y: 46, color: "text-blue-400/80" },
  { label: "GATE", y: 52, color: "text-amber-400/80" },
  { label: "FIX", y: 59, color: "text-orange-400/80" },
  { label: "BUILD", y: 67, color: "text-emerald-400/80" },
  { label: "EVAL", y: 75, color: "text-cyan-400/80" },
  { label: "VALIDATE", y: 81, color: "text-amber-400/80" },
  { label: "SHIP", y: 86, color: "text-emerald-300/90" },
];

export const brainstormPhaseLabels: PhaseLabel[] = [
  { label: "INPUT", y: 10, color: "text-slate-500" },
  { label: "IDEATE", y: 45, color: "text-slate-500" },
  { label: "SYNTH", y: 85, color: "text-purple-400/80" },
];

export const evalCallouts: CalloutDef[] = [];
export const brainstormCallouts: CalloutDef[] = [];

export const GO_NODES = new Set(["doc_gen", "blueprint", "prompt_strategy", "code_gen", "code_eval", "build_validate", "git_push", "ci_test", "app_spec", "do_build", "do_deploy", "verified"]);
export const CONDITIONAL_NODES = new Set(["fix_storm", "scope_down"]);
export const BOTTOM_NODES = new Set([...GO_NODES, ...CONDITIONAL_NODES]);

export function getVisibleNodeIds(
  pipeline: PipelineType,
  nodes: NodeDef[],
  activeNodes: Record<string, NodeStatus>,
): Set<string> {
  const visible = new Set<string>();
  const isLive = Object.keys(activeNodes).length > 0;

  for (const node of nodes) {
    if (pipeline !== "evaluation" || !BOTTOM_NODES.has(node.id)) {
      visible.add(node.id);
      continue;
    }

    if (!isLive) {
      if (GO_NODES.has(node.id) || CONDITIONAL_NODES.has(node.id)) visible.add(node.id);
      continue;
    }

    const decisionStatus = activeNodes.decision || "idle";
    if (decisionStatus !== "complete") continue;

    const isGo = GO_NODES.has(node.id) && [...GO_NODES].some((candidate) => activeNodes[candidate] && activeNodes[candidate] !== "idle");
    const isFix = activeNodes.fix_storm && activeNodes.fix_storm !== "idle";
    const isScopeDown = activeNodes.scope_down && activeNodes.scope_down !== "idle";

    if (isGo && !GO_NODES.has(node.id)) continue;
    if (isFix && node.id !== "fix_storm") continue;
    if (isScopeDown && node.id !== "scope_down" && !GO_NODES.has(node.id)) continue;
    if (!isGo && !isFix && !isScopeDown) {
      visible.add(node.id);
      continue;
    }

    visible.add(node.id);
  }

  return visible;
}

export interface PipelineGraphProps {
  activeNodes?: Record<string, NodeStatus>;
  nodeMetadata?: Record<string, { iteration?: number; maxIterations?: number; repairAttempt?: number; maxRepairs?: number; matchRate?: number; skipped?: boolean }>;
  pipeline?: PipelineType;
  className?: string;
}

export function PipelineGraph({ activeNodes = {}, nodeMetadata = {}, pipeline = "evaluation", className }: PipelineGraphProps) {
  const nodes = pipeline === "evaluation" ? evalNodes : brainstormNodes;
  const edges = pipeline === "evaluation" ? evalEdges : brainstormEdges;
  const phaseLabels = pipeline === "evaluation" ? evalPhaseLabels : brainstormPhaseLabels;
  const phaseDividers = pipeline === "evaluation" ? [7.5, 15.5, 24.5, 33.5, 42.5, 50, 56.5, 64, 72, 79, 83] : [28, 67];
  const callouts = pipeline === "evaluation" ? evalCallouts : brainstormCallouts;
  const getNodeStatus = (id: string): NodeStatus => activeNodes[id] || "idle";
  const visibleNodeIds = getVisibleNodeIds(pipeline, nodes, activeNodes);
  const isOverview = Object.keys(activeNodes).length === 0;
  const visibleEdges = edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target));

  const baseHeight = pipeline === "evaluation" ? "h-[860px] lg:h-[900px]" : "h-[520px] lg:h-[560px]";

  return (
    <Card
      className={cn(
        "relative w-full overflow-hidden border-border/50 bg-card/50 py-0 backdrop-blur-sm",
        "bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.08),transparent_45%),linear-gradient(180deg,rgba(15,23,42,0.28),rgba(2,6,23,0.08))]",
        baseHeight,
        className,
      )}
    >
      <div className="grid h-full grid-cols-[58px_minmax(0,1fr)] md:grid-cols-[72px_minmax(0,1fr)]">
        <div className="relative border-r border-border/40 bg-black/15">
          {phaseLabels.map((phase) => (
            <span
              key={phase.label}
              className={cn(
                "absolute left-2 -translate-y-1/2 text-[9px] font-semibold uppercase tracking-[0.18em] md:left-3",
                phase.color,
              )}
              style={{ top: toVerticalPercent(phase.y) }}
            >
              {phase.label}
            </span>
          ))}
        </div>

        <div className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-blue-500/8 via-transparent to-transparent" />

          <div className="absolute right-4 top-4 z-20 flex flex-wrap justify-end gap-2">
            <Badge variant="outline" className="border-slate-500/30 bg-slate-900/40 text-slate-200">
              Idle
            </Badge>
            <Badge variant="outline" className="border-blue-500/30 bg-blue-500/12 text-blue-100">
              Active
            </Badge>
            <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/12 text-emerald-100">
              Complete
            </Badge>
          </div>

          <svg
            className="pointer-events-none absolute inset-0 h-full w-full opacity-20"
            viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
            preserveAspectRatio="none"
          >
            <title>Phase Dividers</title>
            {phaseDividers.map((y) => (
              <line
                key={y}
                x1="4"
                y1={y}
                x2="96"
                y2={y}
                stroke="rgba(148,163,184,0.38)"
                strokeWidth={0.22}
                strokeDasharray="1.5,1"
                vectorEffect="non-scaling-stroke"
              />
            ))}
          </svg>

          <svg
            className="pointer-events-none absolute inset-0 h-full w-full"
            viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
            preserveAspectRatio="none"
          >
            <title>Pipeline Flow</title>
            <defs>
              <style>{SVG_STYLES}</style>
              <marker id="arr-idle" viewBox="0 0 10 8" refX="10" refY="4" markerWidth="5" markerHeight="4" orient="auto-start-reverse">
                <path d="M 0 0 L 10 4 L 0 8 z" fill={EDGE_COLORS.idle} />
              </marker>
              <marker id="arr-active" viewBox="0 0 10 8" refX="10" refY="4" markerWidth="6" markerHeight="5" orient="auto-start-reverse">
                <path d="M 0 0 L 10 4 L 0 8 z" fill={EDGE_COLORS.active} />
              </marker>
              <marker id="arr-complete" viewBox="0 0 10 8" refX="10" refY="4" markerWidth="5" markerHeight="4" orient="auto-start-reverse">
                <path d="M 0 0 L 10 4 L 0 8 z" fill={EDGE_COLORS.complete} />
              </marker>
              <filter id="edge-glow">
                <feGaussianBlur stdDeviation="2" />
              </filter>
              <filter id="particle-glow">
                <feGaussianBlur stdDeviation="0.9" />
              </filter>
            </defs>

            {visibleEdges.map((edge) => {
              const src = nodes.find((node) => node.id === edge.source);
              const tgt = nodes.find((node) => node.id === edge.target);
              if (!src || !tgt) return null;

              return (
                <PipelineEdge
                  key={`${edge.source}-${edge.target}`}
                  edge={edge}
                  sourceNode={src}
                  targetNode={tgt}
                  sourceStatus={getNodeStatus(edge.source)}
                  targetStatus={getNodeStatus(edge.target)}
                />
              );
            })}

            {isOverview && <ParticleLayer pipeline={pipeline} nodes={nodes} />}
          </svg>

          {callouts.map((callout) => (
            <div
              key={callout.label}
              className={cn(
                "pointer-events-none absolute z-10 hidden -translate-y-1/2 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] md:block",
                callout.className,
              )}
              style={{ left: `${callout.x}%`, top: toVerticalPercent(callout.y) }}
            >
              {callout.label}
            </div>
          ))}

          <motion.div variants={containerVariants} initial="hidden" animate="visible" className="absolute inset-0">
            {nodes.map((node) => {
              if (!visibleNodeIds.has(node.id)) return null;

              return (
                <PipelineNode
                  key={node.id}
                  node={node}
                  status={getNodeStatus(node.id)}
                  isOverview={isOverview}
                  isConditional={CONDITIONAL_NODES.has(node.id)}
                  meta={nodeMetadata[node.id]}
                  topStyle={toVerticalPercent(node.y)}
                />
              );
            })}
          </motion.div>
        </div>
      </div>
    </Card>
  );
}
