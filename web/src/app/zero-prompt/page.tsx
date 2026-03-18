"use client";

import { useState, useEffect, useRef } from "react";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Rocket, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useZeroPrompt } from "@/hooks/use-zero-prompt";
import { StatusBar } from "@/components/zero-prompt/status-bar";
import { KanbanBoard } from "@/components/zero-prompt/kanban-board";
import { ActionFeed } from "@/components/zero-prompt/action-feed";

export default function ZeroPromptPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background flex items-center justify-center"><p className="text-muted-foreground">Loading...</p></div>}>
      <ZeroPromptInner />
    </Suspense>
  );
}

function ZeroPromptInner() {
  const { 
    session, 
    actions, 
    isConnected, 
    isLoading, 
    error, 
    startSession, 
    queueBuild, 
    passCard 
  } = useZeroPrompt();
  
  const [goal, setGoal] = useState<string>("");
  const searchParams = useSearchParams();
  const autostartFired = useRef(false);

  useEffect(() => {
    if (searchParams.get("autostart") === "true" && !session && !isLoading && !autostartFired.current) {
      autostartFired.current = true;
      startSession(10);
    }
  }, [searchParams, session, isLoading, startSession]);

  const handleStart = () => {
    const goalNum = parseInt(goal, 10);
    startSession(isNaN(goalNum) ? undefined : goalNum);
  };

  if (!session) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-4">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-md w-full space-y-6 text-center"
        >
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight flex items-center justify-center gap-2">
              <Rocket className="w-8 h-8 text-blue-500" />
              Zero-Prompt Mode
            </h1>
            <p className="text-muted-foreground">
              Autonomous YouTube exploration and app deployment.
            </p>
          </div>

          {error && (
            <Alert variant="destructive" className="text-left">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-4 bg-card border border-border/50 p-6 rounded-xl shadow-sm">
            <div className="space-y-2 text-left">
              <label htmlFor="goal-input" className="text-sm font-medium">Target Apps (Optional)</label>
              <Input 
                id="goal-input"
                type="number" 
                placeholder="e.g. 5" 
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                min={1}
              />
              <p className="text-xs text-muted-foreground">
                How many apps should the agent try to deploy before stopping?
              </p>
            </div>
            
            <Button 
              className="w-full h-12 text-lg font-semibold" 
              onClick={handleStart}
              disabled={isLoading}
            >
              {isLoading ? "Starting..." : "Start Autonomous Agent"}
            </Button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground p-4 sm:p-6 lg:p-8">
      <div className="max-w-[1600px] mx-auto space-y-6">
        <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight flex items-center gap-2">
              <Rocket className="w-6 h-6 text-blue-500" />
              Zero-Prompt Dashboard
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Session: {session.session_id} • Status: {session.status}
            </p>
          </div>
        </header>

        <StatusBar session={session} isConnected={isConnected} />
        
        <KanbanBoard 
          cards={session.cards || []} 
          onQueueBuild={queueBuild} 
          onPassCard={passCard} 
        />
        
        <ActionFeed actions={actions} />
      </div>
    </div>
  );
}
