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
  particle?: boolean;
}

const evalNodes: NodeDef[] = [
  { id: "input", label: "Input", x: 50, y: 5, emoji: "📝" },
  { id: "architect", label: "Architect", x: 10, y: 18, emoji: "🏗️" },
  { id: "scout", label: "Scout", x: 30, y: 18, emoji: "🔭" },
  { id: "catalyst", label: "Catalyst", x: 50, y: 18, emoji: "⚡" },
  { id: "guardian", label: "Guardian", x: 70, y: 18, emoji: "🛡️" },
  { id: "advocate", label: "Advocate", x: 90, y: 18, emoji: "🎯" },
  { id: "cross_exam", label: "Cross-Exam", x: 50, y: 31, emoji: "⚔️" },
  { id: "score_tech", label: "Tech", x: 10, y: 44, emoji: "📊" },
  { id: "score_market", label: "Market", x: 30, y: 44, emoji: "📊" },
  { id: "score_innovation", label: "Innovation", x: 50, y: 44, emoji: "📊" },
  { id: "score_risk", label: "Risk", x: 70, y: 44, emoji: "📊" },
  { id: "score_user", label: "User", x: 90, y: 44, emoji: "📊" },
  { id: "verdict", label: "Vibe Score™", x: 50, y: 57, emoji: "🏛️", glow: true },
  { id: "decision", label: "Decision Gate", x: 50, y: 69, emoji: "🚦" },
  { id: "doc_gen", label: "Specs", x: 30, y: 80, emoji: "📄" },
  { id: "code_gen", label: "Full Stack", x: 70, y: 80, emoji: "💻" },
  { id: "github", label: "GitHub", x: 14, y: 92, emoji: "📦" },
  { id: "ci", label: "CI/CD", x: 34, y: 92, emoji: "⚙️" },
  { id: "do_deploy", label: "DO Deploy", x: 58, y: 92, emoji: "🚀" },
  { id: "verified", label: "Live", x: 82, y: 92, emoji: "✅", glow: true },
  { id: "review", label: "Review", x: 50, y: 86 },
  { id: "feedback", label: "Feedback", x: 50, y: 86 },
];

const evalEdges: EdgeDef[] = [
  { source: "input", target: "architect" },
  { source: "input", target: "scout" },
  { source: "input", target: "catalyst", particle: true },
  { source: "input", target: "guardian" },
  { source: "input", target: "advocate" },
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
  { source: "score_innovation", target: "verdict", particle: true },
  { source: "score_risk", target: "verdict" },
  { source: "score_user", target: "verdict" },
  { source: "verdict", target: "decision", particle: true },
  { source: "decision", target: "doc_gen", label: "GO", labelColor: "rgba(16,185,129,0.9)" },
  { source: "doc_gen", target: "code_gen" },
  { source: "code_gen", target: "github" },
  { source: "github", target: "ci" },
  { source: "ci", target: "do_deploy", particle: true },
  { source: "do_deploy", target: "verified" },
  { source: "decision", target: "review" },
  { source: "decision", target: "feedback" },
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
  { source: "input", target: "catalyst", particle: true },
  { source: "input", target: "guardian" },
  { source: "input", target: "advocate" },
  { source: "architect", target: "synthesize" },
  { source: "scout", target: "synthesize" },
  { source: "catalyst", target: "synthesize", particle: true },
  { source: "guardian", target: "synthesize" },
  { source: "advocate", target: "synthesize" },
];

const GO_NODES = new Set(["doc_gen", "code_gen", "github", "ci", "do_deploy", "verified"]);
const BOTTOM_NODES = new Set([...GO_NODES, "review", "feedback"]);

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
      if (GO_NODES.has(node.id)) visible.add(node.id);
      continue;
    }

    const decisionStatus = activeNodes["decision"] || "idle";
    if (decisionStatus !== "complete") continue;

    const isGo = GO_NODES.has(node.id) && [...GO_NODES].some((n) => activeNodes[n] && activeNodes[n] !== "idle");
    const isConditional = activeNodes["review"] && activeNodes["review"] !== "idle";
    const isNoGo = activeNodes["feedback"] && activeNodes["feedback"] !== "idle";

    if (isGo && !GO_NODES.has(node.id)) continue;
    if (isConditional && node.id !== "review") continue;
    if (isNoGo && node.id !== "feedback") continue;
    if (!isGo && !isConditional && !isNoGo) { visible.add(node.id); continue; }

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
        { label: "INPUT", y: "2%", color: "text-slate-500" },
        { label: "COUNCIL", y: "15%", color: "text-slate-500" },
        { label: "DEBATE", y: "28%", color: "text-slate-500" },
        { label: "SCORING", y: "41%", color: "text-slate-500" },
        { label: "VERDICT", y: "54%", color: "text-blue-500/70" },
        { label: "GATE", y: "66%", color: "text-amber-500/70" },
        { label: "GEN", y: "77%", color: "text-emerald-500/60" },
        { label: "SHIP", y: "89%", color: "text-emerald-500/70" },
      ]
    : [
        { label: "INPUT", y: "7%", color: "text-slate-500" },
        { label: "IDEATE", y: "42%", color: "text-slate-500" },
        { label: "SYNTH", y: "82%", color: "text-purple-500/70" },
      ];

  const phaseDividers = pipeline === "evaluation"
    ? [11.5, 24.5, 37.5, 50.5, 63, 74.5, 86]
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

          const showParticle = edge.particle && (isOverview || srcStatus === "complete");
          const particleDur = isOverview ? `${2.2 + idx * 0.3}s` : "1s";
          const particleDelay = `${(idx * 0.4) % 2}s`;

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
              {showParticle && (
                <circle r="1" fill={isOverview ? "rgba(99,166,255,0.7)" : stroke} opacity={0.9}>
                  <animateMotion dur={particleDur} repeatCount="indefinite" begin={particleDelay} path={d} />
                </circle>
              )}
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
