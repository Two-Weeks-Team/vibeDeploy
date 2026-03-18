"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface DecisionGateProps {
  verdict: "GO" | "CONDITIONAL" | "NO-GO";
  score: number;
  suggestions?: string[];
  onProceed?: () => void;
  onRevise?: () => void;
}

export function DecisionGate({
  verdict,
  score,
  suggestions = [],
  onProceed,
  onRevise,
}: DecisionGateProps) {
  const tone =
    verdict === "GO"
      ? "border-emerald-400/25 bg-emerald-500/10"
      : verdict === "CONDITIONAL"
        ? "border-amber-400/25 bg-amber-500/10"
        : "border-red-400/25 bg-red-500/10";

  return (
    <Card className={cn("border-white/10", tone)}>
      <CardHeader>
        <CardTitle>
          {verdict === "GO" && "🟢 GO — Ready to Build"}
          {verdict === "CONDITIONAL" && "🟡 CONDITIONAL — Needs Adjustment"}
          {verdict === "NO-GO" && "🔴 NO-GO — Not Feasible"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <motion.p
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-sm text-muted-foreground"
        >
          Vibe Score: <span className="font-semibold text-foreground">{Math.round(score)}</span>
        </motion.p>
        {suggestions.length > 0 && (
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
            {suggestions.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        )}
        <div className="flex gap-2">
          {verdict !== "NO-GO" && (
            <Button onClick={onProceed}>
              {verdict === "GO" ? "Deploy Now" : "Proceed Anyway"}
            </Button>
          )}
          <Button variant="outline" onClick={onRevise}>
            {verdict === "NO-GO" ? "Try Different Idea" : "Revise Idea"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
