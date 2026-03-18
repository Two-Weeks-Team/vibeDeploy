"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { MousePointer2, Rocket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ZeroPromptLanding } from "@/components/zero-prompt-landing";
import { StatusBar } from "@/components/zero-prompt/status-bar";
import { KanbanBoard } from "@/components/zero-prompt/kanban-board";
import { ActionFeed } from "@/components/zero-prompt/action-feed";
import { useDemoZeroPrompt } from "@/hooks/use-demo-zero-prompt";

type DemoStage = "landing" | "dashboard";

const DEMO_VIDEO_URL = "https://www.youtube.com/watch?v=aADukThvjXQ";
const DEMO_INPUT_CLICK_DELAY_MS = 900;
const DEMO_INPUT_TYPING_START_MS = 1300;
const DEMO_INPUT_TYPING_STEP_MS = 32;
const DEMO_START_BUTTON_MOVE_DELAY_MS = 700;
const DEMO_START_BUTTON_CLICK_DELAY_MS = 1050;
const DEMO_SESSION_START_DELAY_MS = 1360;

const INITIAL_CURSOR = {
  visible: false,
  x: -40,
  y: -40,
  clicking: false,
};

export default function DemoPage() {
  const [stage, setStage] = useState<DemoStage>("landing");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null);
  const [cursor, setCursor] = useState(INITIAL_CURSOR);

  const {
    session,
    actions,
    isConnected,
    isCompleted,
    isLoading,
    startSession,
    queueBuild,
    passCard,
    deleteCard,
    reExplore,
  } = useDemoZeroPrompt();

  const introInputRef = useRef<HTMLInputElement | null>(null);
  const zeroPromptStartRef = useRef<HTMLButtonElement | null>(null);
  const sequenceTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const buildDialogShownRef = useRef(false);
  const buildClickShownRef = useRef(false);
  const viewAppClickShownRef = useRef(false);
  const sessionStartedRef = useRef(false);

  const clearSequenceTimers = useCallback(() => {
    sequenceTimersRef.current.forEach(clearTimeout);
    sequenceTimersRef.current = [];
  }, []);

  const moveCursorToElement = useCallback((element: Element | null, clicking = false) => {
    if (!element) return;
    const rect = element.getBoundingClientRect();
    setCursor({
      visible: true,
      x: rect.left + rect.width * 0.5,
      y: rect.top + rect.height * 0.55,
      clicking,
    });
  }, []);

  const queueTimer = useCallback((callback: () => void, delay: number) => {
    const timer = setTimeout(callback, delay);
    sequenceTimersRef.current.push(timer);
  }, []);

  useEffect(() => {
    if (stage !== "landing") return;
    clearSequenceTimers();
    buildDialogShownRef.current = false;
    buildClickShownRef.current = false;
    viewAppClickShownRef.current = false;
    sessionStartedRef.current = false;

    queueTimer(() => setYoutubeUrl(""), 0);

    queueTimer(() => moveCursorToElement(introInputRef.current), 600);
    queueTimer(() => setCursor((prev) => ({ ...prev, clicking: true })), DEMO_INPUT_CLICK_DELAY_MS);
    queueTimer(() => setCursor((prev) => ({ ...prev, clicking: false })), 1120);

    DEMO_VIDEO_URL.split("").forEach((_, index) => {
      queueTimer(() => {
        setYoutubeUrl(DEMO_VIDEO_URL.slice(0, index + 1));
      }, DEMO_INPUT_TYPING_START_MS + index * DEMO_INPUT_TYPING_STEP_MS);
    });

    const typingCompleteAt = DEMO_INPUT_TYPING_START_MS + DEMO_VIDEO_URL.length * DEMO_INPUT_TYPING_STEP_MS;

    queueTimer(() => moveCursorToElement(zeroPromptStartRef.current), typingCompleteAt + DEMO_START_BUTTON_MOVE_DELAY_MS);
    queueTimer(() => setCursor((prev) => ({ ...prev, clicking: true })), typingCompleteAt + DEMO_START_BUTTON_CLICK_DELAY_MS);
    queueTimer(() => setCursor((prev) => ({ ...prev, clicking: false })), typingCompleteAt + 1240);
    queueTimer(() => {
      if (sessionStartedRef.current) return;
      sessionStartedRef.current = true;
      startSession();
    }, typingCompleteAt + DEMO_SESSION_START_DELAY_MS);
    queueTimer(() => {
      setStage("dashboard");
    }, typingCompleteAt + DEMO_SESSION_START_DELAY_MS + 900);

    return clearSequenceTimers;
  }, [clearSequenceTimers, moveCursorToElement, queueTimer, stage, startSession]);

  useEffect(() => {
    if (stage === "dashboard" && !session && !isLoading) {
      if (sessionStartedRef.current) return;
      sessionStartedRef.current = true;
      startSession();
    }
  }, [stage, session, isLoading, startSession]);

  useEffect(() => {
    if (stage !== "dashboard" || !session || buildDialogShownRef.current) return;

    const readyCards = session.cards.filter((card) => card.status === "go_ready");
    const buildAlreadyStarted = session.cards.some((card) => ["build_queued", "building", "deployed"].includes(card.status));
    const targetCard = readyCards.find((card) => card.card_id === "nutriplan-aADukT");
    const studyMateGoSeen = actions.some((action) => action.message.includes("StudyMate Lite scored 75.0 → GO"));

    if (!targetCard || buildAlreadyStarted || !studyMateGoSeen) return;

    buildDialogShownRef.current = true;
    queueTimer(() => {
      const cardElement = document.querySelector('[data-card-id="nutriplan-aADukT"]');
      moveCursorToElement(cardElement);
    }, 400);
    queueTimer(() => {
      setCursor((prev) => ({ ...prev, clicking: true }));
      setSelectedCardId("nutriplan-aADukT");
    }, 760);
    queueTimer(() => setCursor((prev) => ({ ...prev, clicking: false })), 980);
    queueTimer(() => setSelectedCardId(null), 5760);
  }, [actions, moveCursorToElement, queueTimer, session, stage]);

  useEffect(() => {
    if (stage !== "dashboard" || !session || buildClickShownRef.current) return;

    const thresholdReached = actions.some((action) => action.message.includes("[4/4] threshold reached"));
    const targetCard = session.cards.find((card) => card.card_id === "nutriplan-aADukT");

    if (!thresholdReached || !targetCard || targetCard.status !== "go_ready") return;

    buildClickShownRef.current = true;
    queueTimer(() => setSelectedCardId(null), 0);

    queueTimer(() => {
      const goButton = document.querySelector('[data-go-card-id="nutriplan-aADukT"]');
      moveCursorToElement(goButton);
    }, 260);
    queueTimer(() => {
      setCursor((prev) => ({ ...prev, clicking: true }));
      queueBuild("nutriplan-aADukT");
    }, 610);
    queueTimer(() => setCursor((prev) => ({ ...prev, clicking: false })), 860);
  }, [actions, moveCursorToElement, queueBuild, queueTimer, session, stage]);

  useEffect(() => {
    if (stage !== "dashboard" || !session || viewAppClickShownRef.current) return;

    const targetCard = session.cards.find((card) => card.card_id === "nutriplan-aADukT");
    if (!targetCard || targetCard.status !== "deployed") return;

    viewAppClickShownRef.current = true;
    queueTimer(() => {
      const viewAppLink = document.querySelector('[data-view-app-card-id="nutriplan-aADukT"]');
      moveCursorToElement(viewAppLink);
    }, 900);
    queueTimer(() => {
      setCursor((prev) => ({ ...prev, clicking: true }));
      const viewAppLink = document.querySelector('[data-view-app-card-id="nutriplan-aADukT"]');
      if (viewAppLink instanceof HTMLElement) {
        viewAppLink.click();
      }
    }, 1700);
    queueTimer(() => setCursor((prev) => ({ ...prev, clicking: false })), 2100);
  }, [moveCursorToElement, queueTimer, session, stage]);

  useEffect(() => () => clearSequenceTimers(), [clearSequenceTimers]);

  return (
    <>
      <AnimatePresence mode="wait">
        {stage === "landing" && (
          <motion.div key="landing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }}>
            <ZeroPromptLanding
              youtubeUrl={youtubeUrl}
              onYoutubeUrlChange={setYoutubeUrl}
              inputRef={introInputRef}
              startAction={
                <Button ref={zeroPromptStartRef} size="lg" className="h-14 px-8 text-lg font-bold gap-2 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600">
                  <Rocket className="w-5 h-5" />
                  Zero-Prompt Start
                </Button>
              }
            />
          </motion.div>
        )}

        {stage === "dashboard" && session && (
        <motion.div
          key="dashboard"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
          className="min-h-screen bg-background text-foreground p-4 sm:p-6 lg:p-8"
        >
          <div className="max-w-[1600px] mx-auto space-y-6">
            <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold tracking-tight flex items-center gap-2">
                  <Rocket className="w-6 h-6 text-blue-500" />
                   Zero-Prompt Workspace
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Session: {session.session_id.slice(0, 8)}... &bull; Status: {session.status}
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
                ) : null}
              </div>
            </header>
            <StatusBar session={session} isConnected={isConnected} />
            <KanbanBoard
              cards={session.cards || []}
              onQueueBuild={queueBuild}
              onPassCard={passCard}
              onDeleteCard={deleteCard}
              onReExplore={reExplore}
              autoCloseMs={5000}
              selectedCardId={selectedCardId}
              onSelectedCardChange={setSelectedCardId}
            />
            <ActionFeed actions={actions} />
          </div>
        </motion.div>
      )}

      </AnimatePresence>

      <motion.div
        className="pointer-events-none fixed left-0 top-0 z-[120]"
        initial={false}
        animate={{
          opacity: cursor.visible ? 1 : 0,
          x: cursor.x,
          y: cursor.y,
          scale: cursor.clicking ? 0.92 : 1,
        }}
        transition={{ type: "spring", stiffness: 420, damping: 28, mass: 0.5 }}
      >
        <div className="relative -translate-x-2 -translate-y-2">
          <MousePointer2 className="h-6 w-6 fill-white text-slate-900 drop-shadow-[0_2px_8px_rgba(0,0,0,0.35)]" />
          {cursor.clicking && <span className="absolute -inset-2 rounded-full border border-white/70 bg-white/15" />}
        </div>
      </motion.div>
    </>
  );
}
