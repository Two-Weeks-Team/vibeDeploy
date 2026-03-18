"use client";

import { useEffect, useRef } from "react";
import { Rocket } from "lucide-react";
import { useZeroPrompt } from "@/hooks/use-zero-prompt";
import { StatusBar } from "@/components/zero-prompt/status-bar";
import { KanbanBoard } from "@/components/zero-prompt/kanban-board";
import { ActionFeed } from "@/components/zero-prompt/action-feed";

export default function ZeroPromptPage() {
  const hasStartedRef = useRef(false);
  const {
    session,
    actions,
    isConnected,
    isCompleted,
    isLoading,
    hasLoadedDashboard,
    startSession,
    queueBuild,
    passCard,
    deleteCard,
  } = useZeroPrompt();

  useEffect(() => {
    if (hasLoadedDashboard && !session && !isLoading && !hasStartedRef.current) {
      hasStartedRef.current = true;
      startSession(5);
    }
  }, [session, isLoading, hasLoadedDashboard, startSession]);

  return (
    <div className="min-h-screen bg-background text-foreground p-4 sm:p-6 lg:p-8">
      <div className="max-w-[1600px] mx-auto space-y-6">
        <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight flex items-center gap-2">
              <Rocket className="w-6 h-6 text-blue-500" />
              Zero-Prompt Workspace
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              {session
                ? `Session: ${session.session_id.slice(0, 8)}... • Status: ${session.status}`
                : isLoading ? "Starting..." : "Connecting to agent..."}
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
                <span className="text-yellow-500">Starting...</span>
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
          }}
        />

        <ActionFeed actions={actions} />
      </div>
    </div>
  );
}
