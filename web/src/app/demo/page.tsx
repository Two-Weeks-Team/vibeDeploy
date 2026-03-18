"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { Rocket, Youtube, FlaskConical, Code2, Globe, Play, ExternalLink, Lock, MousePointer2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import Image from "next/image";

function extractVideoId(url: string): string | null {
  try {
    const u = new URL(url);
    const rawId = u.hostname.includes("youtube.com") ? u.searchParams.get("v") : u.hostname === "youtu.be" ? u.pathname.slice(1) : null;
    if (!rawId || rawId.length < 11) return null;
    return rawId.slice(0, 11);
  } catch { /* ignore */ }
  return null;
}
import { StatusBar } from "@/components/zero-prompt/status-bar";
import { KanbanBoard } from "@/components/zero-prompt/kanban-board";
import { ActionFeed } from "@/components/zero-prompt/action-feed";
import { useDemoZeroPrompt } from "@/hooks/use-demo-zero-prompt";

type DemoStage = "landing" | "dashboard";

const DEMO_VIDEO_URL = "https://www.youtube.com/watch?v=aADukThvjXQ";

const INITIAL_CURSOR = {
  visible: false,
  x: -40,
  y: -40,
  clicking: false,
};

const COUNCIL_AGENTS = [
  { emoji: "\u{1F3D7}\uFE0F", name: "Architect", role: "Technical Lead" },
  { emoji: "\u{1F52D}", name: "Scout", role: "Market Analyst" },
  { emoji: "\u{1F6E1}\uFE0F", name: "Guardian", role: "Risk Assessor" },
  { emoji: "\u26A1", name: "Catalyst", role: "Innovation Officer" },
  { emoji: "\u{1F3AF}", name: "Advocate", role: "UX Champion" },
  { emoji: "\u{1F9ED}", name: "Strategist", role: "Session Lead" },
];

const STEPS = [
  { num: "1", title: "Discover", desc: "AI explores YouTube for trending app ideas", icon: Youtube },
  { num: "2", title: "Evaluate", desc: "Vibe Council scores feasibility with 6 agents", icon: FlaskConical },
  { num: "3", title: "Build", desc: "PRD, code, and assets auto-generated", icon: Code2 },
  { num: "4", title: "Deploy", desc: "Live app on DigitalOcean in minutes", icon: Globe },
];

const containerVariants = { hidden: {}, visible: { transition: { staggerChildren: 0.08 } } };
const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};
const cardItem = {
  hidden: { opacity: 0, y: 16, scale: 0.95 },
  visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.35, ease: "easeOut" as const } },
};

export default function DemoPage() {
  const [stage, setStage] = useState<DemoStage>("landing");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const videoId = extractVideoId(youtubeUrl);
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

  const autoFired = useRef(false);
  const introInputRef = useRef<HTMLInputElement | null>(null);
  const zeroPromptStartRef = useRef<HTMLButtonElement | null>(null);
  const sequenceTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const buildDialogShownRef = useRef(false);
  const buildClickShownRef = useRef(false);
  const viewAppClickShownRef = useRef(false);

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
    if (stage !== "landing" || autoFired.current) return;
    autoFired.current = true;
    clearSequenceTimers();
    buildDialogShownRef.current = false;
    buildClickShownRef.current = false;
    viewAppClickShownRef.current = false;

    queueTimer(() => moveCursorToElement(introInputRef.current), 600);
    queueTimer(() => setCursor((prev) => ({ ...prev, clicking: true })), 900);
    queueTimer(() => setCursor((prev) => ({ ...prev, clicking: false })), 1120);

    DEMO_VIDEO_URL.split("").forEach((_, index) => {
      queueTimer(() => setYoutubeUrl(DEMO_VIDEO_URL.slice(0, index + 1)), 1300 + index * 32);
    });

    const typingCompleteAt = 1300 + DEMO_VIDEO_URL.length * 32;
    queueTimer(() => moveCursorToElement(zeroPromptStartRef.current), typingCompleteAt + 700);
    queueTimer(() => setCursor((prev) => ({ ...prev, clicking: true })), typingCompleteAt + 1050);
    queueTimer(() => setCursor((prev) => ({ ...prev, clicking: false })), typingCompleteAt + 1240);
    queueTimer(() => {
      startSession();
      setStage("dashboard");
    }, typingCompleteAt + 1360);

    return clearSequenceTimers;
  }, [clearSequenceTimers, moveCursorToElement, queueTimer, stage, startSession]);

  useEffect(() => {
    if (stage === "dashboard" && !session && !isLoading) {
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
        <motion.div
          key="landing"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4 }}
          className="flex min-h-screen flex-col items-center justify-center px-4 py-16 relative"
        >
          <div className="absolute top-4 right-4">
            <Link href="/dashboard">
              <Button variant="outline" size="sm" className="gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><title>Dashboard</title><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>
                Dashboard
              </Button>
            </Link>
          </div>
          <div className="w-full max-w-2xl space-y-12">
            <motion.div className="space-y-4 text-center" initial="hidden" animate="visible" variants={containerVariants}>
              <motion.h1 variants={fadeUp} className="text-5xl font-bold tracking-tight sm:text-6xl bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                vibeDeploy
              </motion.h1>
              <motion.p variants={fadeUp} className="text-xl font-medium text-foreground">
                Zero prompts. Zero coding. One button deploys a live app.
              </motion.p>
              <motion.p variants={fadeUp} className="text-sm text-muted-foreground/70">
                AI discovers ideas from YouTube, validates with research, writes code, and ships to DigitalOcean — autonomously.
              </motion.p>
            </motion.div>

            <motion.div className="text-center space-y-3" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25, duration: 0.5 }}>
              <Button ref={zeroPromptStartRef} size="lg" className="h-14 px-8 text-lg font-semibold bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400 text-white rounded-full shadow-lg shadow-purple-500/25">
                <Rocket className="w-5 h-5 mr-2" />
                Zero-Prompt Start
              </Button>
              <p className="text-sm text-muted-foreground/70">
                Press Start. AI discovers, validates, and deploys apps autonomously.
              </p>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.5 }}>
              <div className="relative my-10">
                <div className="absolute inset-0 flex items-center" aria-hidden="true">
                  <div className="w-full border-t border-border/50" />
                </div>
                <div className="relative flex justify-center">
                  <span className="bg-background px-4 text-sm text-muted-foreground">Or start from a YouTube video</span>
                </div>
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35, duration: 0.5 }}>
              <Card className="border-border/50 overflow-hidden">
                <CardContent className="pt-6 space-y-4">
                  <div className="flex gap-2">
                    <Input
                      ref={introInputRef}
                      value={youtubeUrl}
                      onChange={(e) => setYoutubeUrl(e.target.value)}
                      placeholder="https://www.youtube.com/watch?v=..."
                      className="font-mono text-sm"
                    />
                    <Button
                      className="shrink-0 gap-2 bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400"
                      onClick={() => alert("This feature is restricted to admin users and authorized IPs only.")}
                    >
                      <Lock className="w-4 h-4" />
                      Start
                    </Button>
                  </div>

                  {videoId && (
                    <a href={youtubeUrl} target="_blank" rel="noopener noreferrer" className="block group">
                      <div className="flex items-center gap-2 mb-2">
                        <Youtube className="w-5 h-5 text-red-500" />
                        <span className="text-sm font-medium">YouTube</span>
                      </div>
                      <p className="text-sm text-blue-400 group-hover:underline mb-3 flex items-center gap-1">
                        {youtubeUrl}
                        <ExternalLink className="w-3 h-3" />
                      </p>
                      <div className="relative aspect-video rounded-lg overflow-hidden bg-muted">
                        <Image
                          src={`https://img.youtube.com/vi/${videoId}/hqdefault.jpg`}
                          alt="YouTube video thumbnail"
                          fill
                          className="object-cover"
                          unoptimized
                        />
                        <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/30 transition-colors">
                          <div className="w-16 h-16 rounded-full bg-black/60 flex items-center justify-center">
                            <Play className="w-8 h-8 text-white fill-white ml-1" />
                          </div>
                        </div>
                      </div>
                    </a>
                  )}

                  {!videoId && youtubeUrl.length > 0 && (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      Paste a valid YouTube URL to see the preview.
                    </p>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4, duration: 0.5 }}>
              <div className="relative my-10">
                <div className="absolute inset-0 flex items-center" aria-hidden="true">
                  <div className="w-full border-t border-border/50" />
                </div>
                <div className="relative flex justify-center">
                  <span className="bg-background px-4 text-sm text-muted-foreground">How it works</span>
                </div>
              </div>
            </motion.div>

            <motion.div
              className="grid grid-cols-2 gap-4 sm:grid-cols-4"
              initial="hidden"
              animate="visible"
              variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.1, delayChildren: 0.45 } } }}
            >
              {STEPS.map((step) => {
                const Icon = step.icon;
                return (
                  <motion.div key={step.num} variants={fadeUp}>
                    <Card className="text-center border-border/50 h-full">
                      <CardContent className="pt-5 space-y-2">
                        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                          <Icon className="w-5 h-5 text-primary" />
                        </div>
                        <p className="text-sm font-semibold">{step.title}</p>
                        <p className="text-xs text-muted-foreground leading-relaxed">{step.desc}</p>
                      </CardContent>
                    </Card>
                  </motion.div>
                );
              })}
            </motion.div>

            <motion.div
              className="grid grid-cols-2 gap-3 sm:grid-cols-3"
              initial="hidden"
              animate="visible"
              variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.08, delayChildren: 0.6 } } }}
            >
              {COUNCIL_AGENTS.map((agent) => (
                <motion.div key={agent.name} variants={cardItem} whileHover={{ scale: 1.05, y: -2 }} transition={{ type: "spring", stiffness: 400, damping: 20 }}>
                  <Card className="text-center transition-shadow hover:shadow-lg hover:shadow-primary/5 border-border/50">
                    <CardContent className="pt-4">
                      <div className="text-2xl">{agent.emoji}</div>
                      <p className="mt-1 text-sm font-medium">{agent.name}</p>
                      <p className="text-xs text-muted-foreground">{agent.role}</p>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          </div>
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
                  Zero-Prompt Dashboard
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
