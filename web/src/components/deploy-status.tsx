"use client";

import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

type DeployStep = "repo" | "push" | "deploy" | "live" | "failed";

interface DeployStatusProps {
  currentStep: DeployStep;
  repoUrl?: string;
  liveUrl?: string;
  error?: string;
  status?: string;
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
  status,
}: DeployStatusProps) {
  const isGithubOnly = status === "github_only";
  
  const effectiveSteps = isGithubOnly 
    ? [
        { key: "repo", label: "Creating GitHub repo" },
        { key: "push", label: "Pushing code" },
        { key: "deploy", label: "DigitalOcean (Skipped)" },
      ] as const
    : STEPS;

  const currentIndex = effectiveSteps.findIndex((s) => s.key === currentStep);
  const clampedIndex = currentIndex < 0 ? 0 : currentIndex;
  
  let percent = 0;
  if (currentStep === "live") {
    percent = 100;
  } else if (isGithubOnly && currentStep === "push") {
    percent = 66;
  } else {
    percent = Math.round((clampedIndex / (effectiveSteps.length - 1)) * 100);
  }

  return (
    <Card className="border-white/10 bg-card/60">
      <CardHeader>
        <CardTitle>Deployment</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Progress value={percent} />
        {effectiveSteps.map((step, i) => {
          const isDone = i < clampedIndex || currentStep === "live" || (isGithubOnly && currentStep === "push" && i <= 1);
          const isCurrent = step.key === currentStep && !isGithubOnly;
          const isSkipped = isGithubOnly && step.key === "deploy";

          return (
            <motion.div
              key={step.key}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: i * 0.03 }}
              className="flex items-center gap-2 text-sm"
            >
              {isDone && !isSkipped && <span className="text-emerald-400">✓</span>}
              {isCurrent && currentStep !== "live" && !isSkipped && <span className="animate-pulse">●</span>}
              {isSkipped && <span className="text-muted-foreground">⏭</span>}
              {!isDone && !isCurrent && !isSkipped && (
                <span className="text-muted-foreground">○</span>
              )}
              <span className={isCurrent ? "font-medium" : "text-muted-foreground"}>
                {step.label}
              </span>
            </motion.div>
          );
        })}

        {isGithubOnly && currentStep === "push" && (
          <div className="text-sm text-muted-foreground italic mt-2">
            Local mode — DO deployment skipped
          </div>
        )}

        {currentStep === "failed" && error && (
          <Badge variant="destructive">{error}</Badge>
        )}

        {repoUrl && (
          <a
            href={repoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="block text-sm text-blue-300 underline"
          >
            View Repository
          </a>
        )}

        {liveUrl && !isGithubOnly && (
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
