"use client";

import { Badge } from "@/components/ui/badge";

/**
 * VibeScore — Displays the Vibe Score™ with visual indicator.
 * ≥75 = GO (green), 50-74 = CONDITIONAL (yellow), <50 = NO-GO (red).
 * TODO (Wave 6): Animated score reveal, breakdown chart, axis scores.
 */

interface VibeScoreProps {
  score: number;
  breakdown?: {
    tech: number;
    market: number;
    innovation: number;
    risk: number;
    userImpact: number;
  };
}

export function VibeScore({ score, breakdown }: VibeScoreProps) {
  const verdict =
    score >= 75 ? "GO" : score >= 50 ? "CONDITIONAL" : "NO-GO";
  const color =
    score >= 75
      ? "bg-green-500/20 text-green-400"
      : score >= 50
        ? "bg-yellow-500/20 text-yellow-400"
        : "bg-red-500/20 text-red-400";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="text-5xl font-bold">{score}</div>
      <Badge className={color}>{verdict}</Badge>
      {breakdown && (
        <div className="mt-2 grid grid-cols-5 gap-2 text-xs text-muted-foreground">
          <div>Tech: {breakdown.tech}</div>
          <div>Market: {breakdown.market}</div>
          <div>Innovation: {breakdown.innovation}</div>
          <div>Risk: {breakdown.risk}</div>
          <div>UX: {breakdown.userImpact}</div>
        </div>
      )}
    </div>
  );
}
