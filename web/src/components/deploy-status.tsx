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
  localUrl?: string;
  localBackendUrl?: string;
  localFrontendUrl?: string;
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
  localUrl,
  localBackendUrl,
  localFrontendUrl,
}: DeployStatusProps) {
  const isGithubOnly = status === "github_only";
  const isLocalRunning = status === "local_running";
  
  const effectiveSteps = isGithubOnly || isLocalRunning
    ? [
        { key: "repo" as DeployStep, label: "Creating GitHub repo" },
        { key: "push" as DeployStep, label: "Pushing code" },
        { key: "deploy" as DeployStep, label: isLocalRunning ? "Local server started" : "DigitalOcean (Skipped)" },
        ...(isLocalRunning ? [{ key: "live" as DeployStep, label: "Running locally" }] : []),
      ]
    : STEPS;

  const isFailed = currentStep === "failed";
  const lookupStep = isFailed ? "deploy" : currentStep;
  const currentIndex = effectiveSteps.findIndex((s) => s.key === lookupStep);
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
          const isCurrentStep = step.key === lookupStep && !isGithubOnly;
          const isSkipped = isGithubOnly && step.key === "deploy";
          const isErrorStep = isFailed && step.key === "deploy";

          return (
            <motion.div
              key={step.key}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: i * 0.03 }}
              className="flex items-center gap-2 text-sm"
            >
              {isDone && !isSkipped && !isErrorStep && <span className="text-emerald-400">✓</span>}
              {isErrorStep && <span className="text-red-400">✗</span>}
              {isCurrentStep && !isFailed && currentStep !== "live" && !isSkipped && <span className="animate-pulse">●</span>}
              {isSkipped && <span className="text-muted-foreground">⏭</span>}
              {!isDone && !isCurrentStep && !isSkipped && !isErrorStep && (
                <span className="text-muted-foreground">○</span>
              )}
              <span className={isErrorStep ? "font-medium text-red-400" : isCurrentStep ? "font-medium" : "text-muted-foreground"}>
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

        {isLocalRunning && (
          <div className="mt-3 space-y-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
            <div className="flex items-center gap-2 text-sm font-medium text-emerald-400">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              Running locally
            </div>
            {localFrontendUrl && (
              <a href={localFrontendUrl} target="_blank" rel="noopener noreferrer" className="block text-sm text-blue-300 underline">
                Frontend → {localFrontendUrl}
              </a>
            )}
            {localBackendUrl && (
              <a href={localBackendUrl} target="_blank" rel="noopener noreferrer" className="block text-sm text-blue-300 underline">
                Backend → {localBackendUrl}
              </a>
            )}
            <p className="text-xs text-muted-foreground">
              To deploy to DigitalOcean, see the README in your GitHub repo.
            </p>
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

        {liveUrl && !isGithubOnly && !isLocalRunning && (
          <Button asChild className="w-full">
            <a href={liveUrl} target="_blank" rel="noopener noreferrer">
              Visit Live App →
            </a>
          </Button>
        )}

        {isLocalRunning && localUrl && (
          <Button asChild className="w-full bg-emerald-600 hover:bg-emerald-700">
            <a href={localUrl} target="_blank" rel="noopener noreferrer">
              Open Local App →
            </a>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
