"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * DeployStatus — Shows deployment progress and live URL.
 * Steps: Creating repo → Pushing code → Deploying to DO → Live.
 * TODO (Wave 8): Real-time deployment progress via SSE, live URL link.
 */

type DeployStep = "repo" | "push" | "deploy" | "live" | "failed";

interface DeployStatusProps {
  currentStep: DeployStep;
  repoUrl?: string;
  liveUrl?: string;
  error?: string;
}

const STEPS: { key: DeployStep; label: string }[] = [
  { key: "repo", label: "Creating GitHub repo" },
  { key: "push", label: "Pushing code" },
  { key: "deploy", label: "Deploying to DigitalOcean" },
  { key: "live", label: "Live!" },
];

export function DeployStatus({
  currentStep,
  repoUrl,
  liveUrl,
  error,
}: DeployStatusProps) {
  const currentIndex = STEPS.findIndex((s) => s.key === currentStep);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Deployment</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {STEPS.map((step, i) => {
          const isDone = i < currentIndex || currentStep === "live";
          const isCurrent = step.key === currentStep;
          return (
            <div key={step.key} className="flex items-center gap-2 text-sm">
              {isDone && <span className="text-green-400">✓</span>}
              {isCurrent && currentStep !== "live" && (
                <span className="animate-pulse">●</span>
              )}
              {!isDone && !isCurrent && (
                <span className="text-muted-foreground">○</span>
              )}
              <span className={isCurrent ? "font-medium" : "text-muted-foreground"}>
                {step.label}
              </span>
            </div>
          );
        })}

        {currentStep === "failed" && error && (
          <Badge variant="destructive">{error}</Badge>
        )}

        {repoUrl && (
          <a
            href={repoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="block text-sm text-blue-400 underline"
          >
            View Repository
          </a>
        )}

        {liveUrl && (
          <Button asChild className="w-full">
            <a href={liveUrl} target="_blank" rel="noopener noreferrer">
              Visit Live App →
            </a>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
