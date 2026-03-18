"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { ZPSession, ZPAction, ZPCard } from "@/types/zero-prompt";
import { DEMO_CARDS, DEMO_TIMELINE, DEMO_SPEED_MULTIPLIER } from "@/lib/demo-data";

const DEMO_SESSION_ID = "demo-zp-auto-20260318";

export function useDemoZeroPrompt() {
  const [session, setSession] = useState<ZPSession | null>(null);
  const [actions, setActions] = useState<ZPAction[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const baseTimeRef = useRef<number>(0);

  const cleanup = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const startSession = useCallback(() => {
    setIsLoading(true);
    cleanup();
    baseTimeRef.current = Date.now();

    const loadTimer = setTimeout(() => {
      setIsLoading(false);
      setIsConnected(true);

      setSession({
        session_id: DEMO_SESSION_ID,
        status: "exploring",
        cards: [],
      });

      DEMO_TIMELINE.forEach((event) => {
        const timer = setTimeout(() => {
          const fakeTs = new Date(
            baseTimeRef.current + event.time * DEMO_SPEED_MULTIPLIER,
          ).toISOString();

          if (event.action) {
            setActions((prev) => [{ ...event.action!, timestamp: fakeTs }, ...prev].slice(0, 300));
          }

          if (event.cardUpdate) {
            const { card_id, status, score, ...extra } = event.cardUpdate;

            setSession((prev) => {
              if (!prev) return prev;

              const existingCard = prev.cards.find((c) => c.card_id === card_id);
              let nextCards: ZPCard[];
              const patch = { status, ...(score !== undefined ? { score } : {}), ...extra };

              if (existingCard) {
                nextCards = prev.cards.map((c) =>
                  c.card_id === card_id ? { ...c, ...patch } : c,
                );
              } else {
                const template = DEMO_CARDS.find((c) => c.card_id === card_id);
                if (!template) return prev;
                nextCards = [...prev.cards, { ...template, ...patch }];
              }

              return { ...prev, cards: nextCards };
            });
          }

          if (event.sessionStatus) {
            setSession((prev) =>
              prev ? { ...prev, status: event.sessionStatus! } : prev,
            );
            if (event.sessionStatus === "completed") {
              setIsConnected(false);
            }
          }
        }, event.time);

        timersRef.current.push(timer);
      });
    }, 800);

    timersRef.current.push(loadTimer);
  }, [cleanup]);

  const queueBuild = useCallback((cardId: string) => {
    const now = new Date().toISOString();
    setSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        cards: prev.cards.map((c) =>
          c.card_id === cardId && c.status === "go_ready"
            ? { ...c, status: "build_queued" as const }
            : c,
        ),
      };
    });
    setActions((prev) => [{ type: "build", message: `Manual GO — ${cardId} queued for build`, timestamp: now }, ...prev]);
  }, []);

  const passCard = useCallback((cardId: string) => {
    const now = new Date().toISOString();
    setSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        cards: prev.cards.map((c) =>
          c.card_id === cardId && c.status === "go_ready"
            ? { ...c, status: "passed" as const }
            : c,
        ),
      };
    });
    setActions((prev) => [{ type: "pass", message: `Manual PASS — ${cardId} skipped`, timestamp: now }, ...prev]);
  }, []);

  const deleteCardFn = useCallback((cardId: string) => {
    const now = new Date().toISOString();
    setSession((prev) => {
      if (!prev) return prev;
      return { ...prev, cards: prev.cards.filter((c) => c.card_id !== cardId) };
    });
    setActions((prev) => [{ type: "delete", message: `Card ${cardId} deleted`, timestamp: now }, ...prev]);
  }, []);

  const reExplore = useCallback((cardId: string) => {
    const now = new Date().toISOString();
    setSession((prev) => {
      if (!prev) return prev;
      return { ...prev, cards: prev.cards.filter((c) => c.card_id !== cardId) };
    });
    setActions((prev) => [{ type: "explore", message: `Re-exploring — replaced ${cardId} with new discovery`, timestamp: now }, ...prev]);
  }, []);

  const isCompleted = session?.status === "completed";

  return {
    session,
    actions,
    isConnected,
    isCompleted,
    isLoading,
    error: null as string | null,
    startSession,
    queueBuild,
    passCard,
    deleteCard: deleteCardFn,
    reExplore,
  };
}
