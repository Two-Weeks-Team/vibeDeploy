"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getSession, startSession, queueBuild, passCard } from "@/lib/zero-prompt-api";
import type { ZPSession, ZPAction } from "@/types/zero-prompt";
import { DASHBOARD_API_URL } from "@/lib/api";

export function useZeroPrompt() {
  const [session, setSession] = useState<ZPSession | null>(null);
  const [actions, setActions] = useState<ZPAction[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const sessionIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

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

  const connectSSE = useCallback((id: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    (async () => {
      try {
        const res = await fetch(`${DASHBOARD_API_URL}/zero-prompt/${id}/events`, {
          signal: controller.signal,
        });
        if (!res.ok || !res.body) throw new Error("SSE connect failed");

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
            if (!trimmed || trimmed.startsWith(":")) continue;
            if (!trimmed.startsWith("data: ")) continue;

            try {
              const data = JSON.parse(trimmed.slice(6));
              if (data.type === "action") {
                setActions((prev) => {
                  const newActions = [data.action, ...prev];
                  return newActions.slice(0, 300);
                });
              } else if (data.type === "session_update") {
                setSession(data.session);
              }
            } catch {
            }
          }
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setIsConnected(false);
      }
    })();
  }, []);

  const handleStartSession = async (goal?: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const { session_id } = await startSession(goal);
      sessionIdRef.current = session_id;
      await fetchSession(session_id);
      connectSSE(session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start session");
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

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  return {
    session,
    actions,
    isConnected,
    isLoading,
    error,
    startSession: handleStartSession,
    queueBuild: handleQueueBuild,
    passCard: handlePassCard,
  };
}
