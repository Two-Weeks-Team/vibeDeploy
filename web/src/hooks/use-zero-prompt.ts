"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getDashboard, getSession, startSession, queueBuild, passCard, deleteCard } from "@/lib/zero-prompt-api";
import { DASHBOARD_API_URL } from "@/lib/api";
import type { ZPSession, ZPAction } from "@/types/zero-prompt";

function stringifyValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((item) => stringifyValue(item)).filter(Boolean).join(", ");
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([k, v]) => `${k}: ${stringifyValue(v)}`)
      .join(", ");
  }
  return "";
}

function normalizeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => stringifyValue(item)).filter(Boolean);
}

function normalizeSession(raw: ZPSession | (ZPSession & { session_id?: string | null })): ZPSession | null {
  if (!(raw as { session_id?: string | null }).session_id) return null;
  return {
    ...raw,
    session_id: String((raw as { session_id: string }).session_id),
    cards: (raw.cards || []).map((card) => ({
      ...card,
      title: stringifyValue(card.title) || stringifyValue(card.video_id),
      reason: stringifyValue(card.reason),
      domain: stringifyValue(card.domain),
      video_summary: stringifyValue(card.video_summary),
      insights: normalizeStringArray(card.insights),
      mvp_proposal: card.mvp_proposal
        ? {
            app_name: stringifyValue(card.mvp_proposal.app_name),
            core_feature: stringifyValue(card.mvp_proposal.core_feature),
            tech_stack: stringifyValue(card.mvp_proposal.tech_stack),
            key_pages: normalizeStringArray(card.mvp_proposal.key_pages),
            estimated_days: Number(card.mvp_proposal.estimated_days || 0) || undefined,
          }
        : undefined,
    })),
  };
}

function getActionCategory(type: string, data: Record<string, unknown>): string {
  if (type.startsWith("zp.transcript") || type.startsWith("zp.discovery") || type.startsWith("zp.exploration") || type === "zp.card.registered" || type === "zp.pipeline.started") return "explore";
  if (type.startsWith("zp.council") || type.startsWith("zp.insight") || type.startsWith("zp.paper") || type.startsWith("zp.brainstorm") || type.startsWith("zp.compete")) return "council";
  if (type.startsWith("zp.verdict")) return "verdict";
  if (type === "zp.build.done" || type === "card.build_step" || type === "zp.auto_build.triggered") return "build";
  if (type === "card.update" && data.status === "deployed") return "deploy";
  if (type.startsWith("card.") || type.startsWith("zp.card")) return "card";
  return "event";
}

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
  if (type === "zp.discovery.complete") return `Found ${data.count} trending videos to analyze`;
  if (type === "zp.card.registered") return `New video queued for analysis: "${data.title}"`;
  if (type === "zp.exploration.started") return `Starting autonomous exploration of ${data.total_videos} trending videos`;
  if (type === "card.update") {
    const title = data.title || String(data.card_id || "").slice(0, 8);
    const step = String(data.analysis_step || "");
    if (data.status === "analyzing") {
      if (step === "transcript") return `Extracting transcript from "${title}"...`;
      if (step === "insight") return `Analyzing app idea from "${title}"...`;
      if (step === "papers") return `Searching academic papers for "${title}"...`;
      if (step === "brainstorm") return `Brainstorming novel features for "${title}"...`;
      if (step === "compete") return `Analyzing market competition for "${title}"...`;
      if (step === "verdict") return `Computing GO/NO-GO verdict for "${title}"...`;
      return `Analyzing "${title}"...`;
    }
    if (data.status === "go_ready") return `"${title}" passed validation — ready for build (score: ${data.score || "?"})`;
    if (data.status === "nogo") return `"${title}" did not pass validation — NO-GO`;
    if (data.status === "building") return `Building app from "${title}"...`;
    if (data.status === "deployed") return `"${title}" deployed successfully!`;
    if (data.status === "build_failed") return `Build failed for "${title}"`;
    return `"${title}" status changed to ${data.status}`;
  }
  if (type === "card.enriched") return `Generated video summary, key insights, and MVP proposal for "${data.title || "card"}"`;
  if (type === "card.build_step") {
    const steps: Record<string, string> = { code_gen: "Generating code", validate: "Validating build", github: "Pushing to GitHub", deploy: "Deploying to DigitalOcean" };
    return steps[String(data.build_step)] || `Build step: ${data.build_step}`;
  }
  if (type === "zp.build.done") return data.status === "deployed" ? "App deployed and live!" : "Build failed — will retry or skip";
  if (type === "zp.council.message") return `${data.agent}: ${data.message}`;
  if (type === "zp.auto_build.triggered") return `Auto-build triggered for "${data.title}" (score: ${data.score}) — goal reached!`;
  return type;
}

export function useZeroPrompt() {
  const [session, setSession] = useState<ZPSession | null>(null);
  const [actions, setActions] = useState<ZPAction[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoadedDashboard, setHasLoadedDashboard] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionRef = useRef<ZPSession | null>(null);
  const [eventSessionId, setEventSessionId] = useState<string | null>(null);

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  const loadDashboard = useCallback(async () => {
    try {
      const data = await getDashboard();
      const normalized = normalizeSession(data as ZPSession & { session_id: string | null });
      if (normalized) {
        setSession(normalized);
        setEventSessionId(normalized.session_id);
        setIsCompleted(normalized.status === "completed");
      } else {
        setSession(null);
        setEventSessionId(null);
        if (typeof window !== "undefined") {
          window.localStorage.removeItem("zp_session_id");
        }
      }
    } catch (err) {
      console.error("Failed to load dashboard", err);
    } finally {
      setHasLoadedDashboard(true);
    }
  }, []);

  useEffect(() => {
    const restore = async () => {
      try {
        const storedSessionId = typeof window !== "undefined" ? window.localStorage.getItem("zp_session_id") : null;
        if (storedSessionId) {
          const restored = await getSession(storedSessionId);
          const normalized = normalizeSession(restored as ZPSession & { session_id?: string | null });
          if (normalized) {
            setSession(normalized);
            setEventSessionId(normalized.session_id);
            setIsCompleted(normalized.status === "completed");
            setHasLoadedDashboard(true);
            return;
          }
        }
      } catch {
        if (typeof window !== "undefined") {
          window.localStorage.removeItem("zp_session_id");
        }
      }

      await loadDashboard();
    };

    void restore();
  }, [loadDashboard]);

  useEffect(() => {
    if (!eventSessionId) return;
    const controller = new AbortController();
    let cancelled = false;
    let retryCount = 0;

    const connect = async () => {
      try {
        const res = await fetch(`${DASHBOARD_API_URL}/zero-prompt/events?session_id=${encodeURIComponent(eventSessionId)}`, {
          signal: controller.signal,
        });
        if (!res.ok || !res.body) throw new Error(`SSE failed: ${res.status}`);
        setIsConnected(true);
        retryCount = 0;

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

              if (data.type === "snapshot") {
                if (data.session_id && data.session_id === eventSessionId) {
                  const normalized = normalizeSession(data as ZPSession & { session_id: string | null });
                  if (normalized) {
                    setSession(normalized);
                  }
                }
                continue;
              }

              if (data.session_id && data.session_id !== eventSessionId) {
                continue;
              }

              const rawType = String(data.type || "");
              const category = getActionCategory(rawType, data as Record<string, unknown>);
              const msg = formatEventMessage(data as Record<string, unknown>);
              if (msg && msg !== rawType) {
                setActions((prev) => [{
                  type: category,
                  timestamp: new Date().toISOString(),
                  message: msg,
                }, ...prev].slice(0, 300));
              }

              if (rawType.includes("card") || rawType.includes("verdict") || rawType.includes("session") || rawType.includes("council") || rawType.includes("build")) {
                await loadDashboard();
              }
            } catch (err) {
              if (process.env.NODE_ENV === "development") {
                console.debug("[useZeroPrompt] Ignoring malformed SSE payload", err);
              }
            }
          }
        }

        if (!cancelled) {
          throw new Error("SSE stream ended");
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (!cancelled) {
          setIsConnected(false);
          retryCount += 1;
          const delay = Math.min(1000 * 2 ** Math.min(retryCount, 5), 10000);
          setTimeout(() => {
            if (!cancelled) {
              void connect();
            }
          }, delay);
        }
      }
    };

    void connect();

    return () => {
      cancelled = true;
      controller.abort();
      setIsConnected(false);
    };
  }, [eventSessionId, loadDashboard]);

  const handleStartSession = useCallback(async (goal?: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const started = await startSession(goal);
      const normalized = normalizeSession(started);
      if (normalized) {
        setSession(normalized);
        setEventSessionId(normalized.session_id);
        if (typeof window !== "undefined") {
          window.localStorage.setItem("zp_session_id", normalized.session_id);
        }
      }
      setActions([]);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start");
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleQueueBuild = useCallback(async (cardId: string) => {
    if (!session) return;
    try {
      await queueBuild(session.session_id, cardId);
      await loadDashboard();
    } catch (err) {
      console.error("Failed to queue build", err);
    }
  }, [loadDashboard, session]);

  const handlePassCard = useCallback(async (cardId: string) => {
    if (!session) return;
    try {
      await passCard(session.session_id, cardId);
      await loadDashboard();
    } catch (err) {
      console.error("Failed to pass card", err);
    }
  }, [loadDashboard, session]);

  const handleDeleteCard = useCallback(async (cardId: string) => {
    if (!session) return;
    try {
      await deleteCard(session.session_id, cardId);
      await loadDashboard();
      if (typeof window !== "undefined") {
        window.localStorage.setItem("zp_session_id", session.session_id);
      }
    } catch (err) {
      console.error("Failed to delete card", err);
    }
  }, [loadDashboard, session]);

  return {
    session,
    actions,
    isConnected,
    isCompleted,
    isLoading,
    hasLoadedDashboard,
    error,
    startSession: handleStartSession,
    restoreSession: loadDashboard,
    queueBuild: handleQueueBuild,
    passCard: handlePassCard,
    deleteCard: handleDeleteCard,
  };
}
