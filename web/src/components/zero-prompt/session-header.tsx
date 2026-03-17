"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Play, Pause, Activity } from "lucide-react";
import type { ZPSession } from "@/types/zero-prompt";

interface SessionHeaderProps {
  session: ZPSession;
  onPauseResume: () => void;
}

export function SessionHeader({ session, onPauseResume }: SessionHeaderProps) {
  const isPaused = session.status === "paused";
  const isCompleted = session.status === "completed";

  return (
    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 p-4 bg-card border border-border/50 rounded-xl shadow-sm">
      <div>
        <div className="flex items-center gap-3 mb-1">
          <h2 className="text-lg font-bold">Session {session.session_id.substring(0, 8)}</h2>
          <Badge variant={isCompleted ? "default" : isPaused ? "secondary" : "outline"} className={!isCompleted && !isPaused ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" : ""}>
            {session.status.toUpperCase()}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground flex items-center gap-2">
          <Activity className="w-4 h-4" />
          {session.cards.length} ideas processed
        </p>
      </div>

      {!isCompleted && (
        <Button 
          variant={isPaused ? "default" : "outline"} 
          onClick={onPauseResume}
          className="w-full sm:w-auto"
        >
          {isPaused ? (
            <>
              <Play className="w-4 h-4 mr-2" /> Resume Session
            </>
          ) : (
            <>
              <Pause className="w-4 h-4 mr-2" /> Pause Session
            </>
          )}
        </Button>
      )}
    </div>
  );
}
