"use client";

import { Progress } from "@/components/ui/progress";
import { Loader2 } from "lucide-react";

interface BuildProgressBarProps {
  status: "queued" | "building" | "deploying" | "completed" | "failed";
  progress: number;
  message?: string;
}

export function BuildProgressBar({ status, progress, message }: BuildProgressBarProps) {
  return (
    <div className="w-full space-y-2">
      <div className="flex justify-between items-center text-xs">
        <div className="flex items-center gap-2">
          {(status === "building" || status === "deploying") && (
            <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
          )}
          <span className="font-medium capitalize">{status}</span>
        </div>
        <span className="text-muted-foreground">{progress}%</span>
      </div>
      <Progress value={progress} className="h-2" />
      {message && (
        <p className="text-[10px] text-muted-foreground truncate">{message}</p>
      )}
    </div>
  );
}
