"use client";


import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";

import { cn } from "@/lib/utils";
import { CheckCircle, XCircle, Clock, Activity, Rocket } from "lucide-react";

export type PipelineType = "evaluation" | "brainstorm";
export type NodeStatus = "idle" | "active" | "complete" | "error";

interface PipelineVizProps {
  activeNodes?: Record<string, NodeStatus>;
  pipeline?: PipelineType;
  className?: string;
}

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } },
};

interface NodeDef {
  id: string;
  label: string;
  x: number;
  y: number;
  emoji?: string;
}

interface EdgeDef {
  source: string;
  target: string;
  label?: string;
  labelColor?: string;
}

const evalNodes: NodeDef[] = [
  { id: "input", label: "Input", x: 50, y: 6, emoji: "📝" },
  { id: "architect", label: "Architect", x: 10, y: 20, emoji: "🏗️" },
  { id: "scout", label: "Scout", x: 30, y: 20, emoji: "🔭" },
  { id: "catalyst", label: "Catalyst", x: 50, y: 20, emoji: "⚡" },
  { id: "guardian", label: "Guardian", x: 70, y: 20, emoji: "🛡️" },
  { id: "advocate", label: "Advocate", x: 90, y: 20, emoji: "🎯" },
  { id: "cross_exam", label: "Cross-Exam", x: 50, y: 34, emoji: "⚔️" },
  { id: "score_tech", label: "Tech", x: 10, y: 48, emoji: "📊" },
  { id: "score_market", label: "Market", x: 30, y: 48, emoji: "📊" },
  { id: "score_innovation", label: "Innovation", x: 50, y: 48, emoji: "📊" },
  { id: "score_risk", label: "Risk", x: 70, y: 48, emoji: "📊" },
  { id: "score_user", label: "User", x: 90, y: 48, emoji: "📊" },
  { id: "verdict", label: "Vibe Score™", x: 50, y: 62, emoji: "🏛️" },
  { id: "decision", label: "Decision Gate", x: 50, y: 76, emoji: "🚦" },
  { id: "doc_gen", label: "Doc Gen", x: 20, y: 90, emoji: "📄" },
  { id: "code_gen", label: "Code Gen", x: 50, y: 90, emoji: "💻" },
  { id: "deployer", label: "Deploy", x: 80, y: 90, emoji: "🚀" },
  { id: "review", label: "Review", x: 50, y: 90 },
  { id: "feedback", label: "Feedback", x: 80, y: 90 },
];

const evalEdges: EdgeDef[] = [
  { source: "input", target: "architect" },
  { source: "input", target: "scout" },
  { source: "input", target: "catalyst" },
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
  { source: "score_innovation", target: "verdict" },
  { source: "score_risk", target: "verdict" },
  { source: "score_user", target: "verdict" },
  { source: "verdict", target: "decision" },
  { source: "decision", target: "doc_gen", label: "GO", labelColor: "rgba(16,185,129,0.9)" },
  { source: "doc_gen", target: "code_gen" },
  { source: "code_gen", target: "deployer" },
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
  { id: "synthesize", label: "Synthesize", x: 50, y: 85, emoji: "🧭" },
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

function getVisibleNodeIds(
  pipeline: PipelineType,
  nodes: NodeDef[],
  activeNodes: Record<string, NodeStatus>,
): Set<string> {
  const visible = new Set<string>();
  const isLive = Object.keys(activeNodes).length > 0;

  for (const node of nodes) {
    if (pipeline !== "evaluation") {
      visible.add(node.id);
      continue;
    }

    const bottomNodes = ["doc_gen", "code_gen", "deployer", "review", "feedback"];

    if (!bottomNodes.includes(node.id)) {
      visible.add(node.id);
      continue;
    }

    if (!isLive) {
      if (node.id === "review" || node.id === "feedback") continue;
      visible.add(node.id);
      continue;
    }

    const decisionStatus = activeNodes["decision"] || "idle";

    if (decisionStatus !== "complete") {
      continue;
    }

    const isGo =
      (activeNodes["doc_gen"] && activeNodes["doc_gen"] !== "idle") ||
      (activeNodes["code_gen"] && activeNodes["code_gen"] !== "idle") ||
      (activeNodes["deployer"] && activeNodes["deployer"] !== "idle");
    const isConditional = activeNodes["review"] && activeNodes["review"] !== "idle";
    const isNoGo = activeNodes["feedback"] && activeNodes["feedback"] !== "idle";

    if (isGo && (node.id === "review" || node.id === "feedback")) continue;
    if (isConditional && (node.id === "doc_gen" || node.id === "code_gen" || node.id === "deployer" || node.id === "feedback")) continue;
    if (isNoGo && (node.id === "doc_gen" || node.id === "code_gen" || node.id === "deployer" || node.id === "review")) continue;

    visible.add(node.id);
  }

  return visible;
}

export function PipelineViz({ activeNodes = {}, pipeline = "evaluation", className }: PipelineVizProps) {
  const nodes = pipeline === "evaluation" ? evalNodes : brainstormNodes;
  const edges = pipeline === "evaluation" ? evalEdges : brainstormEdges;

  const getNodeStatus = (id: string): NodeStatus => activeNodes[id] || "idle";

  const visibleNodeIds = getVisibleNodeIds(pipeline, nodes, activeNodes);

  const getStatusColor = (status: NodeStatus) => {
    switch (status) {
      case "active": return "border-blue-500 bg-blue-500/20 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.5)]";
      case "complete": return "border-emerald-500 bg-emerald-500/20 text-emerald-400";
      case "error": return "border-red-500 bg-red-500/20 text-red-400";
      default: return "border-slate-600/50 bg-slate-800/40 text-slate-400";
    }
  };

  const getStatusIcon = (status: NodeStatus) => {
    switch (status) {
      case "active": return <Activity className="w-3 h-3 animate-pulse" />;
      case "complete": return <CheckCircle className="w-3 h-3" />;
      case "error": return <XCircle className="w-3 h-3" />;
      default: return <Clock className="w-3 h-3 opacity-50" />;
    }
  };

  const visibleEdges = edges.filter(
    (edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target),
  );

  const isOverview = Object.keys(activeNodes).length === 0;

  return (
    <Card className={cn("relative w-full h-[620px] overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.08),transparent_50%)]", className)}>
      <div className="absolute left-2 top-0 bottom-0 flex flex-col justify-between py-4 z-10 pointer-events-none">
        {pipeline === "evaluation" ? (
          <>
            <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider" style={{ position: "absolute", top: "3%" }}>Input</span>
            <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider" style={{ position: "absolute", top: "17%" }}>Council</span>
            <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider" style={{ position: "absolute", top: "31%" }}>Debate</span>
            <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider" style={{ position: "absolute", top: "45%" }}>Scoring</span>
            <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider" style={{ position: "absolute", top: "59%" }}>Verdict</span>
            <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider" style={{ position: "absolute", top: "73%" }}>Gate</span>
            <span className="text-[10px] font-medium text-emerald-600 uppercase tracking-wider" style={{ position: "absolute", top: "87%" }}>Build</span>
          </>
        ) : (
          <>
            <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider" style={{ position: "absolute", top: "7%" }}>Input</span>
            <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider" style={{ position: "absolute", top: "42%" }}>Ideate</span>
            <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider" style={{ position: "absolute", top: "82%" }}>Synth</span>
          </>
        )}
      </div>

      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20" viewBox="0 0 100 100" preserveAspectRatio="none">
        <title>Phase Dividers</title>
        {pipeline === "evaluation" ? (
          <>
            <line x1="5" y1="13" x2="95" y2="13" stroke="rgba(148,163,184,0.3)" strokeWidth={0.3} strokeDasharray="1,1" vectorEffect="non-scaling-stroke" />
            <line x1="5" y1="27" x2="95" y2="27" stroke="rgba(148,163,184,0.3)" strokeWidth={0.3} strokeDasharray="1,1" vectorEffect="non-scaling-stroke" />
            <line x1="5" y1="41" x2="95" y2="41" stroke="rgba(148,163,184,0.3)" strokeWidth={0.3} strokeDasharray="1,1" vectorEffect="non-scaling-stroke" />
            <line x1="5" y1="55" x2="95" y2="55" stroke="rgba(148,163,184,0.3)" strokeWidth={0.3} strokeDasharray="1,1" vectorEffect="non-scaling-stroke" />
            <line x1="5" y1="69" x2="95" y2="69" stroke="rgba(148,163,184,0.3)" strokeWidth={0.3} strokeDasharray="1,1" vectorEffect="non-scaling-stroke" />
            <line x1="5" y1="83" x2="95" y2="83" stroke="rgba(148,163,184,0.3)" strokeWidth={0.3} strokeDasharray="1,1" vectorEffect="non-scaling-stroke" />
          </>
        ) : (
          <>
            <line x1="5" y1="28" x2="95" y2="28" stroke="rgba(148,163,184,0.3)" strokeWidth={0.3} strokeDasharray="1,1" vectorEffect="non-scaling-stroke" />
            <line x1="5" y1="67" x2="95" y2="67" stroke="rgba(148,163,184,0.3)" strokeWidth={0.3} strokeDasharray="1,1" vectorEffect="non-scaling-stroke" />
          </>
        )}
      </svg>

      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
        <title>Pipeline Edges</title>
        <defs>
          <marker id="arrow-idle" viewBox="0 0 10 8" refX="10" refY="4" markerWidth="6" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 0 L 10 4 L 0 8 z" fill="rgba(148,163,184,0.5)" />
          </marker>
          <marker id="arrow-active" viewBox="0 0 10 8" refX="10" refY="4" markerWidth="6" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 0 L 10 4 L 0 8 z" fill="rgba(59,130,246,0.7)" />
          </marker>
          <marker id="arrow-complete" viewBox="0 0 10 8" refX="10" refY="4" markerWidth="6" markerHeight="5" orient="auto-start-reverse">
            <path d="M 0 0 L 10 4 L 0 8 z" fill="rgba(16,185,129,0.6)" />
          </marker>
        </defs>
        {visibleEdges.map((edge) => {
          const sourceNode = nodes.find((n) => n.id === edge.source);
          const targetNode = nodes.find((n) => n.id === edge.target);
          if (!sourceNode || !targetNode) return null;

          const sourceStatus = getNodeStatus(edge.source);
          const targetStatus = getNodeStatus(edge.target);

          let stroke = "rgba(148,163,184,0.4)";
          let markerId = "arrow-idle";
          if (sourceStatus === "complete" && (targetStatus === "active" || targetStatus === "complete")) {
            stroke = "rgba(59,130,246,0.7)";
            markerId = "arrow-active";
          } else if (sourceStatus === "complete") {
            stroke = "rgba(16,185,129,0.6)";
            markerId = "arrow-complete";
          }

          const midY = (sourceNode.y + targetNode.y) / 2;
          const path = `M ${sourceNode.x} ${sourceNode.y} C ${sourceNode.x} ${midY}, ${targetNode.x} ${midY}, ${targetNode.x} ${targetNode.y}`;

          const labelX = (sourceNode.x + targetNode.x) / 2;
          const labelY = midY;

          return (
            <g key={`${edge.source}-${edge.target}`}>
              <path
                d={path}
                fill="none"
                stroke={stroke}
                strokeWidth={1.5}
                markerEnd={`url(#${markerId})`}
                vectorEffect="non-scaling-stroke"
                className="transition-colors duration-500"
              />
              {edge.label && (
                <text
                  x={labelX - 4}
                  y={labelY}
                  fill={edge.labelColor || "rgba(148,163,184,0.7)"}
                  fontSize="2.5"
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

          return (
            <motion.div
              key={node.id}
              variants={fadeUp}
              className="absolute transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-0.5"
              style={{ left: `${node.x}%`, top: `${node.y}%` }}
            >
              <div
                className={cn(
                  "flex items-center justify-center px-3 py-1.5 rounded-full border text-xs font-medium transition-all duration-500 whitespace-nowrap gap-1.5",
                  getStatusColor(status),
                )}
              >
                {node.emoji ? (
                  <span className="text-[11px]">{node.emoji}</span>
                ) : (
                  <span className="mr-0">{getStatusIcon(status)}</span>
                )}
                {node.label}
                {status !== "idle" && (
                  <span className="ml-0.5">{getStatusIcon(status)}</span>
                )}
              </div>
            </motion.div>
          );
        })}

        {isOverview && pipeline === "evaluation" && (
          <motion.div
            variants={fadeUp}
            className="absolute transform -translate-x-1/2 flex items-center gap-1.5 text-[11px] text-emerald-500/70 font-medium"
            style={{ left: "80%", top: "96%" }}
          >
            <Rocket className="w-3.5 h-3.5" />
            <span>Live on DO</span>
          </motion.div>
        )}
      </motion.div>
    </Card>
  );
}
