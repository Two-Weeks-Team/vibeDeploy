"use client";

import { motion } from "framer-motion";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { PipelineViz } from "@/components/dashboard/pipeline-viz";
import { useBuildMonitor } from "@/hooks/use-build-monitor";
import type { ZPCard } from "@/types/zero-prompt";

interface BuildMonitorCardProps {
  card: ZPCard;
  sessionId: string;
}

export function BuildMonitorCard({ card, sessionId }: BuildMonitorCardProps) {
  const { nodeStatuses, nodeMetadata, currentPhase, currentNode, isDone, finalStatus } = useBuildMonitor(
    sessionId,
    card.card_id,
  );

  return (
    <motion.div
      layoutId={`build-${card.card_id}`}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-card border border-blue-500/30 rounded-lg shadow-lg overflow-hidden"
    >
      <div className="p-3 border-b border-border/50 bg-blue-500/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            {isDone ? (
              finalStatus === "deployed" ? (
                <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
              ) : (
                <XCircle className="w-4 h-4 text-red-500 shrink-0" />
              )
            ) : (
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin shrink-0" />
            )}
            <h4 className="text-sm font-medium truncate">{card.title || card.video_id}</h4>
          </div>
          <Badge variant="outline" className="text-[10px] shrink-0">
            {isDone ? finalStatus : currentPhase || "building"}
          </Badge>
        </div>
        {currentNode && !isDone && (
          <p className="text-[10px] text-muted-foreground mt-1 truncate">
            Current: {currentNode}
          </p>
        )}
      </div>

      <div className="p-2">
        <PipelineViz
          pipeline="evaluation"
          activeNodes={nodeStatuses}
          nodeMetadata={nodeMetadata}
          className="h-[300px]"
        />
      </div>
    </motion.div>
  );
}
