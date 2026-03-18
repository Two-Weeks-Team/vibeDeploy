"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getSession, startSession, queueBuild, passCard, deleteCard } from "@/lib/zero-prompt-api";
import type { ZPSession, ZPAction } from "@/types/zero-prompt";

function formatEventMessage(data: Record<string, unknown>): string {
  const type = String(data.type || "");
  if (type === "zp.session.start") return `Session started (goal: ${data.goal_go_cards} apps)`;
  if (type === "zp.transcript.start") return `Extracting transcript for ${data.video_id}...`;
  if (type === "zp.transcript.complete") return `Transcript: ${data.token_count} tokens (${data.source})`;
  if (type === "zp.insight.start") return `Analyzing idea from ${data.video_title || data.video_id}...`;
  if (type === "zp.insight.complete") return `Idea: ${data.domain} domain, ${data.features_found} features (confidence: ${((data.confidence_score as number) * 100).toFixed(0)}%)`;
  if (type === "zp.paper.search") return `Searching papers: "${data.query}"`;
  if (type === "zp.paper.found") return `Found ${data.total} papers from ${data.source}`;
  if (type === "zp.brainstorm.start") return `Brainstorming "${data.idea}" with ${data.paper_count} papers...`;
  if (type === "zp.brainstorm.complete") return `Brainstorm: ${data.novel_features} features, boost +${((data.novelty_boost as number) * 100).toFixed(0)}%`;
  if (type === "zp.compete.start") return `Analyzing competition for "${data.query}"...`;
  if (type === "zp.compete.complete") return `Competition: ${data.competitors_found} found, saturation: ${data.saturation_level}`;
  if (type === "zp.verdict.go") return `✅ GO (score: ${data.score}) — ${data.reason}`;
  if (type === "zp.verdict.nogo") return `❌ NO-GO (score: ${data.score}) — ${data.reason}`;
  if (type === "zp.session.complete") return "Session complete!";
  if (type === "zp.discovery.start") return "Searching for trending videos...";
  if (type === "zp.discovery.grounding") return "Using Gemini AI to discover trending videos...";
  if (type === "zp.discovery.complete") return `Found ${data.count} trending videos`;
  return type;
}

export function useZeroPrompt() {
  const [session, setSession] = useState<ZPSession | null>(null);
  const [actions, setActions] = useState<ZPAction[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const sessionIdRef = useRef<string | null>(null);

  const fetchSession = useCallback(async (id: string) => {
    try {
      const data = await getSession(id);
      setSession(data);
    } catch (err) {
      console.error("Failed to fetch session", err);
    }
  }, []);

  useEffect(() => {
    if (!session || session.status !== "exploring") return;
    
    const interval = setInterval(() => {
      if (sessionIdRef.current) {
        fetchSession(sessionIdRef.current);
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [session, fetchSession]);

  const handleStartSession = async (goal?: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await startSession(goal);
      if (!response.body) throw new Error("No response body");
      
      setIsConnected(true);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;

          try {
            const data = JSON.parse(trimmed.slice(6));
            
            if (data.type === "zp.session.start" && data.session_id) {
              sessionIdRef.current = data.session_id;
              if (typeof window !== "undefined") {
                window.history.replaceState(null, "", `/zero-prompt?session=${data.session_id}`);
              }
            }
            
            setActions((prev) => {
              const action: ZPAction = {
                type: data.type,
                timestamp: new Date().toISOString(),
                message: formatEventMessage(data),
              };
              return [action, ...prev].slice(0, 300);
            });

            if (data.type?.includes("verdict") && sessionIdRef.current) {
              await fetchSession(sessionIdRef.current);
            }
          } catch {}
        }
      }
      
      if (sessionIdRef.current) {
        await fetchSession(sessionIdRef.current);
      }
      setIsConnected(false);
      setIsCompleted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start");
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQueueBuild = async (cardId: string) => {
    if (!session) return;
    try {
      await queueBuild(session.session_id, cardId);
      await fetchSession(session.session_id);
    } catch (err) {
      console.error("Failed to queue build", err);
    }
  };

  const handlePassCard = async (cardId: string) => {
    if (!session) return;
    try {
      await passCard(session.session_id, cardId);
      await fetchSession(session.session_id);
    } catch (err) {
      console.error("Failed to pass card", err);
    }
  };

  const handleDeleteCard = async (cardId: string) => {
    if (!session) return;
    try {
      await deleteCard(session.session_id, cardId);
      await fetchSession(session.session_id);
    } catch (err) {
      console.error("Failed to delete card", err);
    }
  };

  const restoreSession = useCallback(async (id: string) => {
    sessionIdRef.current = id;
    await fetchSession(id);
    setIsCompleted(true);
  }, [fetchSession]);

  return {
    session,
    actions,
    isConnected,
    isCompleted,
    isLoading,
    error,
    startSession: handleStartSession,
    restoreSession,
    queueBuild: handleQueueBuild,
    passCard: handlePassCard,
    deleteCard: handleDeleteCard,
  };
}
