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
}

interface EdgeDef {
  source: string;
  target: string;
  path?: string;
}

const evalNodes: NodeDef[] = [
  { id: "input", label: "Input", x: 50, y: 5 },
  { id: "architect", label: "Architect", x: 10, y: 20 },
  { id: "scout", label: "Scout", x: 30, y: 20 },
  { id: "catalyst", label: "Catalyst", x: 50, y: 20 },
  { id: "guardian", label: "Guardian", x: 70, y: 20 },
  { id: "advocate", label: "Advocate", x: 90, y: 20 },
  { id: "cross_exam", label: "Cross-Exam", x: 50, y: 35 },
  { id: "score_tech", label: "Tech Score", x: 10, y: 50 },
  { id: "score_market", label: "Market Score", x: 30, y: 50 },
  { id: "score_innovation", label: "Innovation Score", x: 50, y: 50 },
  { id: "score_risk", label: "Risk Score", x: 70, y: 50 },
  { id: "score_user", label: "User Score", x: 90, y: 50 },
  { id: "verdict", label: "Verdict", x: 50, y: 65 },
  { id: "decision", label: "Decision Gate", x: 50, y: 80 },
  { id: "doc_gen", label: "Doc Gen", x: 20, y: 95 },
  { id: "code_gen", label: "Code Gen", x: 50, y: 95 },
  { id: "deployer", label: "Deployer", x: 80, y: 95 },
  { id: "review", label: "Review", x: 50, y: 95 },
  { id: "feedback", label: "Feedback", x: 80, y: 95 },
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
  { source: "decision", target: "doc_gen" },
  { source: "doc_gen", target: "code_gen" },
  { source: "code_gen", target: "deployer" },
  { source: "decision", target: "review" },
  { source: "decision", target: "feedback" },
];

const brainstormNodes: NodeDef[] = [
  { id: "input", label: "Input", x: 50, y: 10 },
  { id: "architect", label: "Architect", x: 10, y: 50 },
  { id: "scout", label: "Scout", x: 30, y: 50 },
  { id: "catalyst", label: "Catalyst", x: 50, y: 50 },
  { id: "guardian", label: "Guardian", x: 70, y: 50 },
  { id: "advocate", label: "Advocate", x: 90, y: 50 },
  { id: "synthesize", label: "Synthesize", x: 50, y: 90 },
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

export function PipelineViz({ activeNodes = {}, pipeline = "evaluation", className }: PipelineVizProps) {
  const nodes = pipeline === "evaluation" ? evalNodes : brainstormNodes;
  const edges = pipeline === "evaluation" ? evalEdges : brainstormEdges;

  const getNodeStatus = (id: string): NodeStatus => activeNodes[id] || "idle";

  const getStatusColor = (status: NodeStatus) => {
    switch (status) {
      case "active": return "border-blue-500 bg-blue-500/20 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.5)]";
      case "complete": return "border-emerald-500 bg-emerald-500/20 text-emerald-400";
      case "error": return "border-red-500 bg-red-500/20 text-red-400";
      default: return "border-border/50 bg-card/50 text-muted-foreground";
    }
  };

  const getStatusIcon = (status: NodeStatus) => {
    switch (status) {
      case "active": return <Activity className="w-3 h-3 animate-pulse" />;
      case "complete": return <CheckCircle className="w-3 h-3" />;
      case "error": return <XCircle className="w-3 h-3" />;
      default: return <Clock className="w-3 h-3" />;
    }
  };

  return (
    <Card className={cn("relative w-full h-[600px] overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.08),transparent_50%)]", className)}>
      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
        <title>Pipeline Visualization</title>
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
        {edges.map((edge) => {
          const sourceNode = nodes.find((n) => n.id === edge.source);
          const targetNode = nodes.find((n) => n.id === edge.target);
          if (!sourceNode || !targetNode) return null;

          const sourceStatus = getNodeStatus(edge.source);
          const targetStatus = getNodeStatus(edge.target);

          let stroke = "rgba(148,163,184,0.5)";
          let markerId = "arrow-idle";
          if (sourceStatus === "complete" && (targetStatus === "active" || targetStatus === "complete")) {
            stroke = "rgba(59,130,246,0.7)";
            markerId = "arrow-active";
          } else if (sourceStatus === "complete") {
            stroke = "rgba(16,185,129,0.6)";
            markerId = "arrow-complete";
          }

          const path = `M ${sourceNode.x} ${sourceNode.y} C ${sourceNode.x} ${(sourceNode.y + targetNode.y) / 2}, ${targetNode.x} ${(sourceNode.y + targetNode.y) / 2}, ${targetNode.x} ${targetNode.y}`;

          return (
            <path
              key={`${edge.source}-${edge.target}`}
              d={path}
              fill="none"
              stroke={stroke}
              strokeWidth={1.5}
              markerEnd={`url(#${markerId})`}
              vectorEffect="non-scaling-stroke"
              className="transition-colors duration-500"
            />
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
          const status = getNodeStatus(node.id);
          
          if (pipeline === "evaluation") {
            const bottomNodes = ["doc_gen", "code_gen", "deployer", "review", "feedback"];
            const decisionStatus = getNodeStatus("decision");

            if (decisionStatus !== "complete") {
              if (bottomNodes.includes(node.id)) return null;
            } else {
              const isGo = getNodeStatus("doc_gen") !== "idle" || getNodeStatus("code_gen") !== "idle" || getNodeStatus("deployer") !== "idle";
              const isConditional = getNodeStatus("review") !== "idle";
              const isNoGo = getNodeStatus("feedback") !== "idle";

              if (isGo && (node.id === "review" || node.id === "feedback")) return null;
              if (isConditional && (node.id === "doc_gen" || node.id === "code_gen" || node.id === "deployer" || node.id === "feedback")) return null;
              if (isNoGo && (node.id === "doc_gen" || node.id === "code_gen" || node.id === "deployer" || node.id === "review")) return null;
            }
          }

          return (
            <motion.div
              key={node.id}
              variants={fadeUp}
              className="absolute transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-1"
              style={{ left: `${node.x}%`, top: `${node.y}%` }}
            >
              <div
                className={cn(
                  "flex items-center justify-center px-3 py-1.5 rounded-full border text-xs font-medium transition-all duration-500 whitespace-nowrap",
                  getStatusColor(status)
                )}
              >
                <span className="mr-1.5">{getStatusIcon(status)}</span>
                {node.label}
              </div>
            </motion.div>
          );
        })}
      </motion.div>
    </Card>
  );
}
