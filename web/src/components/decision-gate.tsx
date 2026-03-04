"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * DecisionGate — Shows the council verdict and user action options.
 * GO: "Deploy Now" button.
 * CONDITIONAL: Shows scope reduction suggestions + "Proceed" / "Revise" buttons.
 * NO-GO: Shows failure reasons + "Try Different Idea" button.
 * TODO (Wave 5): Connect to decision gate API, handle user responses.
 */

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
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {verdict === "GO" && "🟢 GO — Ready to Build"}
          {verdict === "CONDITIONAL" && "🟡 CONDITIONAL — Needs Adjustment"}
          {verdict === "NO-GO" && "🔴 NO-GO — Not Feasible"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-muted-foreground">Vibe Score™: {score}</p>
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
