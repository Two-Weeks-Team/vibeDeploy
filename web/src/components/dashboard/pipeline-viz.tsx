"use client";

import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { CheckCircle, XCircle, Clock, Activity } from "lucide-react";

export type PipelineType = "evaluation" | "brainstorm";
export type NodeStatus = "idle" | "active" | "complete" | "error";

interface PipelineVizProps {
  activeNodes?: Record<string, NodeStatus>;
  pipeline?: PipelineType;
  className?: string;
}

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.35, ease: "easeOut" as const } },
};

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
  label?: string;
  labelColor?: string;
}

const evalNodes: NodeDef[] = [
  { id: "input", label: "Input", x: 50, y: 2, emoji: "📝" },
  { id: "enrich", label: "Enrich", x: 50, y: 8, emoji: "✨" },
  { id: "architect", label: "Architect", x: 10, y: 16, emoji: "🏗️" },
  { id: "scout", label: "Scout", x: 30, y: 16, emoji: "🔭" },
  { id: "catalyst", label: "Catalyst", x: 50, y: 16, emoji: "⚡" },
  { id: "guardian", label: "Guardian", x: 70, y: 16, emoji: "🛡️" },
  { id: "advocate", label: "Advocate", x: 90, y: 16, emoji: "🎯" },
  { id: "cross_exam", label: "Cross-Exam", x: 50, y: 26, emoji: "⚔️" },
  { id: "score_tech", label: "Tech", x: 10, y: 34, emoji: "📊" },
  { id: "score_market", label: "Market", x: 30, y: 34, emoji: "📊" },
  { id: "score_innovation", label: "Innovation", x: 50, y: 34, emoji: "📊" },
  { id: "score_risk", label: "Risk", x: 70, y: 34, emoji: "📊" },
  { id: "score_user", label: "User", x: 90, y: 34, emoji: "📊" },
  { id: "verdict", label: "Vibe Score™", x: 50, y: 43, emoji: "🏛️", glow: true },
  { id: "decision", label: "Decision Gate", x: 50, y: 51, emoji: "🚦" },
  { id: "fix_storm", label: "Fix-Storm", x: 30, y: 59, emoji: "🔧" },
  { id: "scope_down", label: "Scope-Down", x: 70, y: 59, emoji: "📐" },
  { id: "doc_gen", label: "Specs", x: 30, y: 68, emoji: "📄" },
  { id: "code_gen", label: "Code Gen", x: 70, y: 68, emoji: "💻" },
  { id: "git_push", label: "Git Push", x: 10, y: 80, emoji: "📦" },
  { id: "ci_test", label: "CI Test", x: 26, y: 80, emoji: "⚙️" },
  { id: "app_spec", label: "App Spec", x: 42, y: 80, emoji: "📋" },
  { id: "do_build", label: "Build", x: 58, y: 80, emoji: "🏗️" },
  { id: "do_deploy", label: "Deploy", x: 74, y: 80, emoji: "🚀" },
  { id: "verified", label: "Live", x: 90, y: 80, emoji: "✅", glow: true },
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
  { source: "decision", target: "doc_gen", label: "GO", labelColor: "rgba(16,185,129,0.9)" },
  { source: "decision", target: "fix_storm" },
  { source: "decision", target: "scope_down" },
  { source: "fix_storm", target: "architect" },
  { source: "scope_down", target: "doc_gen" },
  { source: "doc_gen", target: "code_gen" },
  { source: "code_gen", target: "git_push" },
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

const GO_NODES = new Set(["doc_gen", "code_gen", "git_push", "ci_test", "app_spec", "do_build", "do_deploy", "verified"]);
const CONDITIONAL_NODES = new Set(["fix_storm", "scope_down"]);
const BOTTOM_NODES = new Set([...GO_NODES, ...CONDITIONAL_NODES]);

const PARTICLE_DUR = "12s";
const EASE = "0.25 0.1 0.25 1";

const EVAL_KT = "0;0.05;0.10;0.15;0.25;0.33;0.40;0.50;0.55;0.62;0.68;0.74;0.80;0.85;0.90;0.95;1";
const EVAL_CY = "2;8;16;16;26;34;34;43;51;68;68;80;80;80;80;80;80";
const EVAL_CX: number[][] = [
  [50,50,10,10,50,10,10,50,50,30,70,10,26,42,58,74,90],
  [50,50,30,30,50,30,30,50,50,30,70,10,26,42,58,74,90],
  [50,50,50,50,50,50,50,50,50,30,70,10,26,42,58,74,90],
  [50,50,70,70,50,70,70,50,50,30,70,10,26,42,58,74,90],
  [50,50,90,90,50,90,90,50,50,30,70,10,26,42,58,74,90],
];
const EVAL_KS = Array(16).fill(EASE).join("; ");

const BS_KT = "0;0.30;0.45;1";
const BS_CY = "10;45;45;85";
const BS_CX: number[][] = [
  [50,10,10,50],
  [50,30,30,50],
  [50,50,50,50],
  [50,70,70,50],
  [50,90,90,50],
];
const BS_KS = Array(3).fill(EASE).join("; ");

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

    const decisionStatus = activeNodes["decision"] || "idle";
    if (decisionStatus !== "complete") continue;

    const isGo = GO_NODES.has(node.id) && [...GO_NODES].some((n) => activeNodes[n] && activeNodes[n] !== "idle");
    const isFix = activeNodes["fix_storm"] && activeNodes["fix_storm"] !== "idle";
    const isScopeDown = activeNodes["scope_down"] && activeNodes["scope_down"] !== "idle";

    if (isGo && !GO_NODES.has(node.id)) continue;
    if (isFix && node.id !== "fix_storm") continue;
    if (isScopeDown && node.id !== "scope_down" && !GO_NODES.has(node.id)) continue;
    if (!isGo && !isFix && !isScopeDown) { visible.add(node.id); continue; }

    visible.add(node.id);
  }

  return visible;
}

const EDGE_COLORS: Record<string, string> = {
  idle: "rgba(148,163,184,0.35)",
  active: "rgba(59,130,246,0.8)",
  complete: "rgba(16,185,129,0.6)",
};

const SVG_STYLES = `
  @keyframes edgeFlow {
    to { stroke-dashoffset: -16; }
  }
  @keyframes edgeFlowFast {
    to { stroke-dashoffset: -16; }
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
  @keyframes glowPulse {
    0%, 100% { opacity: 0; }
    50% { opacity: 0.6; }
  }
  .glow-ring {
    animation: glowPulse 3s ease-in-out infinite;
  }
`;

export function PipelineViz({ activeNodes = {}, pipeline = "evaluation", className }: PipelineVizProps) {
  const nodes = pipeline === "evaluation" ? evalNodes : brainstormNodes;
  const edges = pipeline === "evaluation" ? evalEdges : brainstormEdges;
  const getNodeStatus = (id: string): NodeStatus => activeNodes[id] || "idle";
  const visibleNodeIds = getVisibleNodeIds(pipeline, nodes, activeNodes);
  const isOverview = Object.keys(activeNodes).length === 0;

  const visibleEdges = edges.filter(
    (edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target),
  );

  const getStatusColor = (status: NodeStatus) => {
    switch (status) {
      case "active": return "border-blue-500 bg-blue-500/20 text-blue-300 shadow-[0_0_20px_rgba(59,130,246,0.5)]";
      case "complete": return "border-emerald-500 bg-emerald-500/20 text-emerald-300";
      case "error": return "border-red-500 bg-red-500/20 text-red-400";
      default: return "border-slate-600/40 bg-slate-800/30 text-slate-400";
    }
  };

  const getStatusIcon = (status: NodeStatus) => {
    switch (status) {
      case "active": return <Activity className="w-3 h-3 animate-pulse" />;
      case "complete": return <CheckCircle className="w-3 h-3" />;
      case "error": return <XCircle className="w-3 h-3" />;
      default: return <Clock className="w-3 h-3 opacity-40" />;
    }
  };

  const phaseLabels = pipeline === "evaluation"
    ? [
        { label: "INPUT", y: "1%", color: "text-slate-500" },
        { label: "ENRICH", y: "7%", color: "text-slate-500" },
        { label: "COUNCIL", y: "15%", color: "text-slate-500" },
        { label: "DEBATE", y: "25%", color: "text-slate-500" },
        { label: "SCORING", y: "33%", color: "text-slate-500" },
        { label: "VERDICT", y: "42%", color: "text-blue-500/70" },
        { label: "GATE", y: "50%", color: "text-amber-500/70" },
        { label: "FIX", y: "58%", color: "text-orange-500/70" },
        { label: "GEN", y: "67%", color: "text-emerald-500/60" },
        { label: "SHIP", y: "79%", color: "text-emerald-500/70" },
      ]
    : [
        { label: "INPUT", y: "7%", color: "text-slate-500" },
        { label: "IDEATE", y: "42%", color: "text-slate-500" },
        { label: "SYNTH", y: "82%", color: "text-purple-500/70" },
      ];

  const phaseDividers = pipeline === "evaluation"
    ? [5, 12, 21, 30, 38.5, 47, 55, 63.5, 74]
    : [28, 67];

  return (
    <Card className={cn(
      "relative w-full h-[660px] overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm",
      "bg-[radial-gradient(ellipse_at_top,rgba(59,130,246,0.06),transparent_60%)]",
      className,
    )}>
      <div className="absolute left-2 top-0 bottom-0 z-10 pointer-events-none">
        {phaseLabels.map((p) => (
          <span
            key={p.label}
            className={cn("text-[9px] font-semibold uppercase tracking-[0.12em] absolute", p.color)}
            style={{ top: p.y }}
          >
            {p.label}
          </span>
        ))}
      </div>

      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-15" viewBox="0 0 100 100" preserveAspectRatio="none">
        <title>Phase Dividers</title>
        {phaseDividers.map((y) => (
          <line key={y} x1="5" y1={y} x2="95" y2={y} stroke="rgba(148,163,184,0.4)" strokeWidth={0.2} strokeDasharray="1.5,1" vectorEffect="non-scaling-stroke" />
        ))}
      </svg>

      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
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
            <feGaussianBlur stdDeviation="1.5" />
          </filter>
        </defs>

        {visibleEdges.map((edge, idx) => {
          const src = nodes.find((n) => n.id === edge.source);
          const tgt = nodes.find((n) => n.id === edge.target);
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
          }

          const midY = (src.y + tgt.y) / 2;
          const d = `M ${src.x} ${src.y} C ${src.x} ${midY}, ${tgt.x} ${midY}, ${tgt.x} ${tgt.y}`;

          return (
            <g key={`${edge.source}-${edge.target}`}>
              {showGlow && (
                <path d={d} fill="none" stroke={stroke} strokeWidth={4} filter="url(#edge-glow)" opacity={0.35} vectorEffect="non-scaling-stroke" />
              )}
              <path
                d={d}
                fill="none"
                stroke={stroke}
                strokeWidth={1.5}
                markerEnd={`url(#${marker})`}
                vectorEffect="non-scaling-stroke"
                className={cn(edgeClass, "transition-colors duration-300")}
              />
              {edge.label && (
                <text
                  x={(src.x + tgt.x) / 2 - 4}
                  y={midY}
                  fill={edge.labelColor || "rgba(148,163,184,0.7)"}
                  fontSize="2.8"
                  fontWeight="bold"
                  textAnchor="end"
                  dominantBaseline="middle"
                >
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}

        {(pipeline === "evaluation" ? EVAL_CX : BS_CX).map((cxArr) => {
          const kt = pipeline === "evaluation" ? EVAL_KT : BS_KT;
          const cy = pipeline === "evaluation" ? EVAL_CY : BS_CY;
          const ks = pipeline === "evaluation" ? EVAL_KS : BS_KS;
          const cx = cxArr.join(";");
          const particleId = `p-${cxArr[1]}`;
          return (
            <g key={particleId}>
              <circle r="0.7" fill="rgba(99,166,255,0.85)">
                <animate attributeName="cx" dur={PARTICLE_DUR} repeatCount="indefinite" values={cx} keyTimes={kt} calcMode="spline" keySplines={ks} />
                <animate attributeName="cy" dur={PARTICLE_DUR} repeatCount="indefinite" values={cy} keyTimes={kt} calcMode="spline" keySplines={ks} />
              </circle>
              <circle r="2" fill="rgba(59,130,246,0.15)" filter="url(#particle-glow)">
                <animate attributeName="cx" dur={PARTICLE_DUR} repeatCount="indefinite" values={cx} keyTimes={kt} calcMode="spline" keySplines={ks} />
                <animate attributeName="cy" dur={PARTICLE_DUR} repeatCount="indefinite" values={cy} keyTimes={kt} calcMode="spline" keySplines={ks} />
              </circle>
            </g>
          );
        })}
      </svg>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="absolute inset-0"
      >
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
              className="absolute transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center"
              style={{ left: `${node.x}%`, top: `${node.y}%` }}
            >
              {shouldGlow && (
                <div
                  className="absolute inset-0 rounded-full glow-ring pointer-events-none"
                  style={{
                    boxShadow: status === "active"
                      ? "0 0 24px 6px rgba(59,130,246,0.4)"
                      : node.id === "verified"
                        ? "0 0 18px 4px rgba(16,185,129,0.3)"
                        : "0 0 16px 4px rgba(59,130,246,0.2)",
                  }}
                />
              )}
              <div
                className={cn(
                  "relative flex items-center justify-center px-2.5 py-1 rounded-full border text-[11px] font-medium transition-all duration-500 whitespace-nowrap gap-1",
                  getStatusColor(status),
                  isOverview && CONDITIONAL_NODES.has(node.id) && "border-dashed opacity-60"
                )}
              >
                {node.emoji && <span className="text-[11px] leading-none">{node.emoji}</span>}
                {!node.emoji && <span>{getStatusIcon(status)}</span>}
                {node.label}
                {status !== "idle" && <span className="ml-0.5">{getStatusIcon(status)}</span>}
              </div>
            </motion.div>
          );
        })}
      </motion.div>
    </Card>
  );
}
