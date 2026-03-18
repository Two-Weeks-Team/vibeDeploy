"use client";

import { useState, useEffect, useCallback } from "react";
import { getDashboard, startSession, queueBuild, passCard, deleteCard } from "@/lib/zero-prompt-api";
import { DASHBOARD_API_URL } from "@/lib/api";
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

  const loadDashboard = useCallback(async () => {
    try {
      const data = await getDashboard();
      if (data.session_id) {
        setSession(data as ZPSession);
        setIsCompleted(data.status === "completed");
      }
    } catch (err) {
      console.error("Failed to load dashboard", err);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    const controller = new AbortController();
    
    (async () => {
      try {
        const res = await fetch(`${DASHBOARD_API_URL}/zero-prompt/events`, {
          signal: controller.signal,
        });
        if (!res.ok || !res.body) return;
        setIsConnected(true);
        
        const reader = res.body.getReader();
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
              setActions(prev => [{
                type: data.type,
                timestamp: new Date().toISOString(),
                message: formatEventMessage(data),
              }, ...prev].slice(0, 300));
              
              if (data.type?.includes("card") || data.type?.includes("verdict") || data.type?.includes("session")) {
                await loadDashboard();
              }
            } catch {}
          }
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
      } finally {
        setIsConnected(false);
      }
    })();
    
    return () => controller.abort();
  }, [loadDashboard]);

  const handleStartSession = async (goal?: number) => {
    setIsLoading(true);
    setError(null);
    try {
      await startSession(goal);
      await loadDashboard();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start");
    } finally {
      setIsLoading(false);
    }
  };

  const handleQueueBuild = async (cardId: string) => {
    if (!session) return;
    try {
      await queueBuild(session.session_id, cardId);
      await loadDashboard();
    } catch (err) {
      console.error("Failed to queue build", err);
    }
  };

  const handlePassCard = async (cardId: string) => {
    if (!session) return;
    try {
      await passCard(session.session_id, cardId);
      await loadDashboard();
    } catch (err) {
      console.error("Failed to pass card", err);
    }
  };

  const handleDeleteCard = async (cardId: string) => {
    if (!session) return;
    try {
      await deleteCard(session.session_id, cardId);
      await loadDashboard();
    } catch (err) {
      console.error("Failed to delete card", err);
    }
  };

  return {
    session,
    actions,
    isConnected,
    isCompleted,
    isLoading,
    error,
    startSession: handleStartSession,
    restoreSession: loadDashboard,
    queueBuild: handleQueueBuild,
    passCard: handlePassCard,
    deleteCard: handleDeleteCard,
  };
}