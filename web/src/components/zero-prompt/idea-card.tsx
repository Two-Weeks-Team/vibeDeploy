"use client";

import { motion } from "framer-motion";
import {
  Play, X, ExternalLink, Loader2, Trash2, CheckCircle,
  Code, Rocket, FileCode, TestTube, Search, BookOpen,
  Brain, TrendingUp, Gavel, RefreshCw, FileText,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ZPCard } from "@/types/zero-prompt";

interface IdeaCardProps {
  card: ZPCard;
  onQueueBuild: (cardId: string) => void;
  onPassCard: (cardId: string) => void;
  onDeleteCard?: (cardId: string) => void;
  onReExplore?: (cardId: string) => void;
  onClick?: (card: ZPCard) => void;
}

export function IdeaCard({ card, onQueueBuild, onPassCard, onDeleteCard, onReExplore, onClick }: IdeaCardProps) {
  return (
    <motion.div
      layoutId={card.card_id}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-card border border-border/50 rounded-lg shadow-sm overflow-hidden cursor-pointer hover:border-primary/50 transition-colors"
      onClick={() => onClick?.(card)}
    >
      <div className="p-3">
        <div className="flex justify-between items-start mb-2">
          <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-5 bg-background truncate max-w-[120px]">
            {card.video_id}
          </Badge>
          {card.score > 0 && (
            <span className={`text-xs font-bold ${card.score >= 70 ? "text-emerald-500" : card.score >= 50 ? "text-amber-500" : "text-red-500"}`}>
              {card.score.toFixed(1)}
            </span>
          )}
        </div>
        <h4 className="text-sm font-medium line-clamp-2 mb-2" title={card.title}>
          {card.title || card.video_id}
        </h4>

        {card.status === "analyzing" && (
          <AnalysisProgress step={card.analysis_step || "transcript"} domain={card.domain} papersFound={card.papers_found} />
        )}

        {card.status === "go_ready" && (
          <div className="flex gap-2 mt-3" onClick={(e) => e.stopPropagation()}>
            <Button size="sm" className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white h-8 text-xs" onClick={() => onQueueBuild(card.card_id)}>
              <Play className="w-3 h-3 mr-1" /> GO!
            </Button>
            <Button size="sm" variant="outline" className="flex-1 h-8 text-xs" onClick={() => onPassCard(card.card_id)}>
              <X className="w-3 h-3 mr-1" /> Pass
            </Button>
          </div>
        )}

        {card.status === "build_queued" && (
          <div className="flex items-center justify-center gap-2 mt-3 text-xs text-muted-foreground bg-muted/50 py-1.5 rounded">
            <Loader2 className="w-3 h-3 animate-spin" />
            Queued...
          </div>
        )}

        {card.status === "building" && (
          <BuildProgress step={card.build_step || "code_gen"} />
        )}

        {card.status === "deployed" && (
          <div className="mt-3 space-y-2" onClick={(e) => e.stopPropagation()}>
            {card.domain && <p className="text-[10px] text-muted-foreground">Domain: {card.domain}</p>}
            <Button size="sm" variant="outline" className="w-full h-8 text-xs border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10" asChild>
              <a href={card.thread_id ? `/result/${card.thread_id}` : `https://${card.card_id}.ondigitalocean.app`} target={card.thread_id ? undefined : "_blank"} rel={card.thread_id ? undefined : "noopener noreferrer"}>
                <ExternalLink className="w-3 h-3 mr-1" /> View App
              </a>
            </Button>
          </div>
        )}

        {(card.status === "nogo" || card.status === "passed" || card.status === "build_failed") && (
          <div className="mt-3 space-y-1.5" onClick={(e) => e.stopPropagation()}>
            {card.reason && <p className="text-[10px] text-muted-foreground line-clamp-2">{card.reason}</p>}
            <div className="flex gap-2">
              {onDeleteCard && (
                <Button size="sm" variant="ghost" className="flex-1 h-7 text-xs text-destructive hover:text-destructive hover:bg-destructive/10" onClick={() => onDeleteCard(card.card_id)}>
                  <Trash2 className="w-3 h-3 mr-1" /> Delete
                </Button>
              )}
              {onReExplore && (
                <Button size="sm" variant="ghost" className="flex-1 h-7 text-xs text-blue-500 hover:text-blue-500 hover:bg-blue-500/10" onClick={() => onReExplore(card.card_id)}>
                  <RefreshCw className="w-3 h-3 mr-1" /> Re-explore
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

const ANALYSIS_STEPS = [
  { key: "transcript", icon: FileText, label: "Transcript" },
  { key: "insight", icon: Brain, label: "Insight" },
  { key: "papers", icon: BookOpen, label: "Papers" },
  { key: "brainstorm", icon: Brain, label: "Brainstorm" },
  { key: "compete", icon: TrendingUp, label: "Competition" },
  { key: "verdict", icon: Gavel, label: "Verdict" },
] as const;

function AnalysisProgress({ step, domain, papersFound }: { step: string; domain?: string; papersFound?: number }) {
  const stepOrder = ANALYSIS_STEPS.map((s) => s.key);
  const currentIdx = stepOrder.indexOf(step as typeof stepOrder[number]);

  return (
    <div className="mt-2 space-y-1.5">
      <div className="flex items-center gap-1.5 text-xs text-purple-400">
        <Search className="w-3 h-3 animate-pulse" />
        <span className="font-medium">Exploring...</span>
      </div>
      <div className="space-y-0.5">
        {ANALYSIS_STEPS.map((s, i) => {
          const done = i < currentIdx;
          const active = i === currentIdx;
          const Icon = s.icon;
          let extra = "";
          if (done && s.key === "insight" && domain) extra = ` → ${domain}`;
          if (done && s.key === "papers" && papersFound) extra = ` → ${papersFound}`;
          return (
            <div key={s.key} className="flex items-center gap-1.5 text-[10px]">
              {done ? (
                <CheckCircle className="w-2.5 h-2.5 text-emerald-500 shrink-0" />
              ) : active ? (
                <Loader2 className="w-2.5 h-2.5 animate-spin text-purple-400 shrink-0" />
              ) : (
                <Icon className="w-2.5 h-2.5 text-muted-foreground/20 shrink-0" />
              )}
              <span className={done ? "text-emerald-500/70" : active ? "text-purple-400 font-medium" : "text-muted-foreground/20"}>
                {s.label}{extra}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const BUILD_STEPS = [
  { key: "code_gen", icon: FileCode, label: "Code Gen" },
  { key: "validate", icon: TestTube, label: "Validate" },
  { key: "github", icon: Code, label: "GitHub" },
  { key: "deploy", icon: Rocket, label: "Deploy" },
] as const;

function BuildProgress({ step }: { step: string }) {
  const stepOrder = BUILD_STEPS.map((s) => s.key);
  const currentIdx = stepOrder.indexOf(step as typeof stepOrder[number]);

  return (
    <div className="mt-2 space-y-1.5">
      <div className="flex items-center gap-1.5 text-xs text-blue-400">
        <Loader2 className="w-3 h-3 animate-spin" />
        <span className="font-medium">Building...</span>
      </div>
      <div className="space-y-0.5">
        {BUILD_STEPS.map((s, i) => {
          const done = i < currentIdx || step === "done";
          const active = i === currentIdx && step !== "done";
          const Icon = s.icon;
          return (
            <div key={s.key} className="flex items-center gap-1.5 text-[10px]">
              {done ? (
                <CheckCircle className="w-2.5 h-2.5 text-emerald-500 shrink-0" />
              ) : active ? (
                <Loader2 className="w-2.5 h-2.5 animate-spin text-blue-400 shrink-0" />
              ) : (
                <Icon className="w-2.5 h-2.5 text-muted-foreground/20 shrink-0" />
              )}
              <span className={done ? "text-emerald-500/70" : active ? "text-blue-400 font-medium" : "text-muted-foreground/20"}>
                {s.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
