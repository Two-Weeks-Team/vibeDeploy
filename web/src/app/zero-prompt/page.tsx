"use client";

import { useState } from "react";
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
  const { 
    session, 
    actions, 
    isConnected, 
    isCompleted,
    isLoading, 
    error, 
    startSession, 
    queueBuild, 
    passCard,
    deleteCard
  } = useZeroPrompt();
  
  const [goal, setGoal] = useState<string>("");

  const handleStart = () => {
    const goalNum = parseInt(goal, 10);
    startSession(isNaN(goalNum) ? undefined : goalNum);
  };

  const showKanban = session || isLoading || actions.length > 0;

  if (!showKanban) {
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
              AI discovers trending YouTube videos, validates with papers, and deploys apps autonomously.
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
              <label htmlFor="goal-input" className="text-sm font-medium">Target GO Ideas</label>
              <Input 
                id="goal-input"
                type="number" 
                placeholder="10" 
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                min={1}
                max={30}
              />
              <p className="text-xs text-muted-foreground">
                How many validated app ideas should the agent collect?
              </p>
            </div>
            
            <Button 
              className="w-full h-12 text-lg font-semibold bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600" 
              onClick={handleStart}
              disabled={isLoading}
            >
              <Rocket className="w-5 h-5 mr-2" />
              {isLoading ? "Starting..." : "Start Zero-Prompt"}
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
              {session 
                ? `Session: ${session.session_id.slice(0, 8)}... • Status: ${session.status}` 
                : "Connecting to agent..."}
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm">
            {isConnected ? (
              <>
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-green-500">Live — Exploring</span>
              </>
            ) : isCompleted ? (
              <>
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                <span className="text-blue-500">Complete</span>
              </>
            ) : isLoading ? (
              <>
                <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
                <span className="text-yellow-500">Connecting...</span>
              </>
            ) : null}
          </div>
        </header>

        <StatusBar session={session} isConnected={isConnected} />
        
        <KanbanBoard 
          cards={session?.cards || []} 
          sessionId={session?.session_id}
          onQueueBuild={queueBuild} 
          onPassCard={passCard}
          onDeleteCard={deleteCard}
          onReExplore={(cardId) => {
            deleteCard(cardId);
            startSession(1);
          }}
        />
        
        <ActionFeed actions={actions} />
      </div>
    </div>
  );
}