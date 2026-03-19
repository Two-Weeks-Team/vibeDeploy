"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Rocket } from "lucide-react";
import { useZeroPrompt } from "@/hooks/use-zero-prompt";
import { StatusBar } from "@/components/zero-prompt/status-bar";
import { KanbanBoard } from "@/components/zero-prompt/kanban-board";
import { ActionFeed } from "@/components/zero-prompt/action-feed";
import type { ZPSession } from "@/types/zero-prompt";

const DEFAULT_GOAL = 5;

export function ZeroPromptWorkspace({ initialSession }: { initialSession: ZPSession | null }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const hasAutostartedRef = useRef(false);
  const autostart = searchParams.get("autostart") === "true";
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
    deleteRejectedCards,
  } = useZeroPrompt(initialSession);

  useEffect(() => {
    if (!autostart || !hasLoadedDashboard || isLoading || hasAutostartedRef.current) {
      return;
    }

    hasAutostartedRef.current = true;

    void (async () => {
      const started = await startSession(DEFAULT_GOAL);
      if (started) {
        router.replace("/zero-prompt");
      }
    })();
  }, [autostart, hasLoadedDashboard, isLoading, router, startSession]);

  return (
    <div className="min-h-screen bg-background p-4 text-foreground sm:p-6 lg:p-8">
      <div className="mx-auto max-w-[1600px] space-y-6">
        <header className="mb-8 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
              <Rocket className="h-6 w-6 text-blue-500" />
              Zero-Prompt Workspace
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {session
                ? `Session: ${session.session_id.slice(0, 8)}... • Status: ${session.status}`
                : isLoading
                  ? "Starting..."
                  : "Connecting to agent..."}
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm">
            {isConnected ? (
              <>
                <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
                <span className="text-green-500">Live - Exploring</span>
              </>
            ) : isCompleted ? (
              <>
                <span className="h-2 w-2 rounded-full bg-blue-500" />
                <span className="text-blue-500">Complete</span>
              </>
            ) : isLoading ? (
              <>
                <span className="h-2 w-2 animate-pulse rounded-full bg-yellow-500" />
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
          onDeleteRejectedCards={deleteRejectedCards}
          onReExplore={(cardId) => {
            deleteCard(cardId);
          }}
        />

        <ActionFeed actions={actions} />
      </div>
    </div>
  );
}
