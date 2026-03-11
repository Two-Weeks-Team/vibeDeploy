"use client";

import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { CheckCircle, XCircle, Clock, Activity } from "lucide-react";

export type PipelineType = "evaluation" | "brainstorm";
export type NodeStatus = "idle" | "active" | "complete" | "error";

interface PipelineVizProps {
  activeNodes?: Record<string, NodeStatus>;
  pipeline?: PipelineType;
  className?: string;
}

interface NodeDef {
  id: string;
  label: string;
  x: number;
  y: number;
  emoji?: string;
  glow?: boolean;
}

interface EdgeDef {
  source: string;
  target: string;
}

interface PhaseLabel {
  label: string;
  y: number;
  color: string;
}

interface CalloutDef {
  label: string;
  x: number;
  y: number;
  className: string;
}

type ParticleRoute = string[];

const SVG_WIDTH = 100;
const SVG_HEIGHT = 92;

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.35, ease: "easeOut" as const } },
};

const evalNodes: NodeDef[] = [
  { id: "input", label: "Input Processor", x: 50, y: 4, emoji: "📝" },
  { id: "enrich", label: "Enrich Idea", x: 50, y: 11, emoji: "✨" },
  { id: "architect", label: "Architect", x: 10, y: 20, emoji: "🏗️" },
  { id: "scout", label: "Scout", x: 30, y: 20, emoji: "🔭" },
  { id: "catalyst", label: "Catalyst", x: 50, y: 20, emoji: "⚡" },
  { id: "guardian", label: "Guardian", x: 70, y: 20, emoji: "🛡️" },
  { id: "advocate", label: "Advocate", x: 90, y: 20, emoji: "🎯" },
  { id: "cross_exam", label: "Cross Examination", x: 50, y: 29, emoji: "⚔️" },
  { id: "score_tech", label: "Tech Feasibility", x: 10, y: 38, emoji: "📊" },
  { id: "score_market", label: "Market Viability", x: 30, y: 38, emoji: "📊" },
  { id: "score_innovation", label: "Innovation Score", x: 50, y: 38, emoji: "📊" },
  { id: "score_risk", label: "Risk Profile", x: 70, y: 38, emoji: "📊" },
  { id: "score_user", label: "User Impact", x: 90, y: 38, emoji: "📊" },
  { id: "verdict", label: "Strategist Verdict", x: 50, y: 47, emoji: "🏛️", glow: true },
  { id: "decision", label: "Decision Gate", x: 50, y: 53, emoji: "🚦" },
  { id: "fix_storm", label: "Fix Storm", x: 22, y: 60, emoji: "🔧" },
  { id: "scope_down", label: "Scope Down", x: 70, y: 60, emoji: "📐" },
  { id: "doc_gen", label: "Doc Generator", x: 18, y: 68, emoji: "📄" },
  { id: "blueprint", label: "Blueprint Generator", x: 44, y: 68, emoji: "🗺️" },
  { id: "prompt_strategy", label: "Prompt Strategist", x: 62, y: 68, emoji: "🧭" },
  { id: "code_gen", label: "Code Generator", x: 80, y: 68, emoji: "💻" },
  { id: "code_eval", label: "Code Evaluator", x: 50, y: 76, emoji: "✅" },
  { id: "git_push", label: "Git Push", x: 8, y: 86, emoji: "📦" },
  { id: "ci_test", label: "CI Test", x: 24, y: 86, emoji: "⚙️" },
  { id: "app_spec", label: "App Spec", x: 40, y: 86, emoji: "📋" },
  { id: "do_build", label: "Build", x: 56, y: 86, emoji: "🏗️" },
  { id: "do_deploy", label: "Deploy", x: 72, y: 86, emoji: "🚀" },
  { id: "verified", label: "Verified Live", x: 88, y: 86, emoji: "✅", glow: true },
];

const evalEdges: EdgeDef[] = [
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
  { source: "code_eval", target: "git_push" },
  { source: "code_eval", target: "code_gen" },
  { source: "git_push", target: "ci_test" },
  { source: "ci_test", target: "app_spec" },
  { source: "app_spec", target: "do_build" },
  { source: "do_build", target: "do_deploy" },
  { source: "do_deploy", target: "verified" },
];

const brainstormNodes: NodeDef[] = [
  { id: "input", label: "Input", x: 50, y: 10, emoji: "📝" },
  { id: "architect", label: "Architect", x: 10, y: 45, emoji: "🏗️" },
  { id: "scout", label: "Scout", x: 30, y: 45, emoji: "🔭" },
  { id: "catalyst", label: "Catalyst", x: 50, y: 45, emoji: "⚡" },
  { id: "guardian", label: "Guardian", x: 70, y: 45, emoji: "🛡️" },
  { id: "advocate", label: "Advocate", x: 90, y: 45, emoji: "🎯" },
  { id: "synthesize", label: "Synthesize", x: 50, y: 85, emoji: "🧭", glow: true },
];

const brainstormEdges: EdgeDef[] = [
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

const evalPhaseLabels: PhaseLabel[] = [
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
  { label: "SHIP", y: 86, color: "text-emerald-300/90" },
];

const brainstormPhaseLabels: PhaseLabel[] = [
  { label: "INPUT", y: 10, color: "text-slate-500" },
  { label: "IDEATE", y: 45, color: "text-slate-500" },
  { label: "SYNTH", y: 85, color: "text-purple-400/80" },
];

const evalCallouts: CalloutDef[] = [
  { label: "Run Council Agent", x: 84, y: 16.1, className: "border-blue-500/30 bg-blue-500/12 text-blue-200" },
  { label: "Score Axis", x: 84, y: 34.4, className: "border-blue-500/30 bg-blue-500/12 text-blue-200" },
  { label: "Repair loop", x: 8, y: 63.2, className: "border-orange-500/30 bg-orange-500/12 text-orange-200" },
  { label: "GO route", x: 8, y: 71.2, className: "border-emerald-500/30 bg-emerald-500/12 text-emerald-200" },
  { label: "Prompt strategy", x: 56, y: 63.8, className: "border-sky-500/30 bg-sky-500/12 text-sky-200" },
  { label: "Ship chain", x: 79, y: 88.5, className: "border-cyan-500/30 bg-cyan-500/12 text-cyan-200" },
];

const brainstormCallouts: CalloutDef[] = [
  { label: "Five-agent fan-out", x: 14, y: 28, className: "border-slate-500/30 bg-slate-500/10 text-slate-200" },
  { label: "Synthesis lane", x: 74, y: 85, className: "border-purple-500/30 bg-purple-500/12 text-purple-200" },
];

const GO_NODES = new Set(["doc_gen", "blueprint", "prompt_strategy", "code_gen", "code_eval", "git_push", "ci_test", "app_spec", "do_build", "do_deploy", "verified"]);
const CONDITIONAL_NODES = new Set(["fix_storm", "scope_down"]);
const BOTTOM_NODES = new Set([...GO_NODES, ...CONDITIONAL_NODES]);

const EDGE_COLORS: Record<NodeStatus, string> = {
  idle: "rgba(148,163,184,0.35)",
  active: "rgba(59,130,246,0.82)",
  complete: "rgba(16,185,129,0.65)",
  error: "rgba(239,68,68,0.65)",
};

const PARTICLE_DUR_SECONDS = 12;
const PARTICLE_DUR = "12s";
const EVAL_PARTICLE_ROUTES: ParticleRoute[] = [
  ["input", "enrich"],
  ["enrich", "architect", "cross_exam"],
  ["enrich", "scout", "cross_exam"],
  ["enrich", "catalyst", "cross_exam"],
  ["enrich", "guardian", "cross_exam"],
  ["enrich", "advocate", "cross_exam"],
  ["cross_exam", "score_tech", "verdict"],
  ["cross_exam", "score_market", "verdict"],
  ["cross_exam", "score_innovation", "verdict"],
  ["cross_exam", "score_risk", "verdict"],
  ["cross_exam", "score_user", "verdict"],
  ["verdict", "decision"],
  ["decision", "fix_storm", "architect", "cross_exam"],
  ["decision", "fix_storm", "scout", "cross_exam"],
  ["decision", "fix_storm", "catalyst", "cross_exam"],
  ["decision", "fix_storm", "guardian", "cross_exam"],
  ["decision", "fix_storm", "advocate", "cross_exam"],
  ["decision", "scope_down", "doc_gen"],
  ["decision", "doc_gen", "blueprint", "prompt_strategy", "code_gen", "code_eval"],
  ["code_eval", "git_push", "ci_test", "app_spec", "do_build", "do_deploy", "verified"],
];

const BS_PARTICLE_ROUTES: ParticleRoute[] = [
  ["input", "architect", "synthesize"],
  ["input", "scout", "synthesize"],
  ["input", "catalyst", "synthesize"],
  ["input", "guardian", "synthesize"],
  ["input", "advocate", "synthesize"],
];

const SVG_STYLES = `
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

function toVerticalPercent(y: number) {
  return `${(y / SVG_HEIGHT) * 100}%`;
}

function buildEdgeCurve(source: NodeDef, target: NodeDef, includeMove: boolean) {
  const midY = (source.y + target.y) / 2;
  const command = `C ${source.x} ${midY}, ${target.x} ${midY}, ${target.x} ${target.y}`;
  return includeMove ? `M ${source.x} ${source.y} ${command}` : command;
}

function buildParticlePath(nodes: NodeDef[], route: ParticleRoute) {
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  let path = "";

  for (let index = 0; index < route.length - 1; index += 1) {
    const source = nodeMap.get(route[index]);
    const target = nodeMap.get(route[index + 1]);
    if (!source || !target) return null;
    path += `${index === 0 ? "" : " "}${buildEdgeCurve(source, target, index === 0)}`;
  }

  return path || null;
}

function getVisibleNodeIds(
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

export function PipelineViz({ activeNodes = {}, pipeline = "evaluation", className }: PipelineVizProps) {
  const nodes = pipeline === "evaluation" ? evalNodes : brainstormNodes;
  const edges = pipeline === "evaluation" ? evalEdges : brainstormEdges;
  const phaseLabels = pipeline === "evaluation" ? evalPhaseLabels : brainstormPhaseLabels;
  const phaseDividers = pipeline === "evaluation" ? [7.5, 15.5, 24.5, 33.5, 42.5, 50, 56.5, 64, 72, 81] : [28, 67];
  const callouts = pipeline === "evaluation" ? evalCallouts : brainstormCallouts;
  const getNodeStatus = (id: string): NodeStatus => activeNodes[id] || "idle";
  const visibleNodeIds = getVisibleNodeIds(pipeline, nodes, activeNodes);
  const isOverview = Object.keys(activeNodes).length === 0;
  const visibleEdges = edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target));
  const particlePaths = (pipeline === "evaluation" ? EVAL_PARTICLE_ROUTES : BS_PARTICLE_ROUTES)
    .map((route) => buildParticlePath(nodes, route))
    .filter((path): path is string => Boolean(path));

  const getStatusColor = (status: NodeStatus) => {
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
  };

  const getStatusIcon = (status: NodeStatus) => {
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
  };

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

              const srcStatus = getNodeStatus(edge.source);
              const tgtStatus = getNodeStatus(edge.target);

              let stroke = EDGE_COLORS.idle;
              let edgeClass = "edge-idle";
              let marker = "arr-idle";
              let showGlow = false;

              if (srcStatus === "complete" && (tgtStatus === "active" || tgtStatus === "complete")) {
                stroke = EDGE_COLORS.active;
                edgeClass = "edge-active";
                marker = "arr-active";
                showGlow = true;
              } else if (srcStatus === "complete") {
                stroke = EDGE_COLORS.complete;
                edgeClass = "edge-complete";
                marker = "arr-complete";
              } else if (srcStatus === "error" || tgtStatus === "error") {
                stroke = EDGE_COLORS.error;
                edgeClass = "edge-complete";
              }

              const d = buildEdgeCurve(src, tgt, true);

              return (
                <g key={`${edge.source}-${edge.target}`}>
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
            })}

            {isOverview &&
              particlePaths.map((path, index) => {
                const begin = index === 0 ? "0s" : `-${(PARTICLE_DUR_SECONDS * index) / particlePaths.length}s`;
                const particleId = `p-${pipeline}-${index}`;
                return (
                  <g key={particleId}>
                    <circle r="0.38" fill="rgba(125,211,252,0.78)">
                      <animateMotion dur={PARTICLE_DUR} begin={begin} repeatCount="indefinite" path={path} rotate="auto" />
                    </circle>
                    <circle r="1.1" fill="rgba(56,189,248,0.12)" filter="url(#particle-glow)">
                      <animateMotion dur={PARTICLE_DUR} begin={begin} repeatCount="indefinite" path={path} rotate="auto" />
                    </circle>
                  </g>
                );
              })}
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

              const status = getNodeStatus(node.id);
              const shouldGlow = node.glow && (isOverview || status === "active");

              return (
                <motion.div
                  key={node.id}
                  variants={fadeUp}
                  animate={status === "active" ? { scale: [1, 1.08, 1] } : { scale: 1 }}
                  transition={status === "active" ? { repeat: Infinity, duration: 1.8, ease: "easeInOut" } : { duration: 0.3 }}
                  className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center"
                  style={{ left: `${node.x}%`, top: toVerticalPercent(node.y) }}
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
                      isOverview && CONDITIONAL_NODES.has(node.id) && "border-dashed opacity-65",
                    )}
                  >
                    {node.emoji ? <span className="text-[11px] leading-none">{node.emoji}</span> : <span>{getStatusIcon(status)}</span>}
                    <span>{node.label}</span>
                    {status !== "idle" && <span className="ml-0.5">{getStatusIcon(status)}</span>}
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
      </div>
    </Card>
  );
}
