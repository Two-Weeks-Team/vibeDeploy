"use client";

import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface CouncilMemberProps {
  name: string;
  emoji: string;
  role: string;
  color: "amber" | "blue" | "emerald" | "purple" | "rose" | "slate";
  status?: "idle" | "active" | "complete" | "error";
  isSpeaking?: boolean;
  message?: string;
  score?: number;
}

const colorMap = {
  amber: "border-amber-400/40 bg-amber-500/10 text-amber-200",
  blue: "border-blue-400/40 bg-blue-500/10 text-blue-200",
  emerald: "border-emerald-400/40 bg-emerald-500/10 text-emerald-200",
  purple: "border-purple-400/40 bg-purple-500/10 text-purple-200",
  rose: "border-rose-400/40 bg-rose-500/10 text-rose-200",
  slate: "border-slate-400/40 bg-slate-500/10 text-slate-200",
};

const statusLabel: Record<NonNullable<CouncilMemberProps["status"]>, string> = {
  idle: "Idle",
  active: "Analyzing",
  complete: "Done",
  error: "Error",
};

export function CouncilMember({
  name,
  emoji,
  role,
  color,
  status = "idle",
  isSpeaking = false,
  message,
  score,
}: CouncilMemberProps) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28 }}
    >
      <Card
        className={cn(
          "relative overflow-hidden border-white/10 bg-card/50 backdrop-blur-sm",
          status === "active" && "shadow-[0_0_0_1px_rgba(255,255,255,0.12)]",
        )}
      >
        <CardContent className="space-y-3 p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3">
              <motion.div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-xl border text-xl",
                  colorMap[color],
                )}
                animate={status === "active" ? { scale: [1, 1.05, 1] } : { scale: 1 }}
                transition={{ repeat: status === "active" ? Infinity : 0, duration: 1.6 }}
              >
                {emoji}
              </motion.div>
              <div>
                <p className="text-sm font-semibold">{name}</p>
                <p className="text-xs text-muted-foreground">{role}</p>
              </div>
            </div>
            <Badge
              variant="secondary"
              className={cn(
                "text-[10px]",
                status === "active" && "bg-primary/20 text-primary",
                status === "complete" && "bg-emerald-500/20 text-emerald-300",
                status === "error" && "bg-destructive/20 text-destructive",
              )}
            >
              {statusLabel[status]}
            </Badge>
          </div>

          {isSpeaking && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="relative rounded-xl border border-white/10 bg-muted/30 px-3 py-2 text-xs leading-relaxed text-muted-foreground"
            >
              {message ?? "Thinking..."}
            </motion.div>
          )}

          {score !== undefined && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Vibe axis score</span>
              <span className="font-semibold text-foreground">{Math.round(score)}/100</span>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
