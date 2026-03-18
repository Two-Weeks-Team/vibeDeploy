"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { Rocket, Youtube, FlaskConical, Code2, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBar } from "@/components/zero-prompt/status-bar";
import { KanbanBoard } from "@/components/zero-prompt/kanban-board";
import { ActionFeed } from "@/components/zero-prompt/action-feed";
import { useDemoZeroPrompt } from "@/hooks/use-demo-zero-prompt";

type DemoStage = "landing" | "dashboard";

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

  useEffect(() => {
    if (stage !== "landing" || autoFired.current) return;
    autoFired.current = true;
    const timer = setTimeout(() => {
      startSession();
      setStage("dashboard");
    }, 5000);
    return () => clearTimeout(timer);
  }, [stage, startSession]);

  useEffect(() => {
    if (stage === "dashboard" && !session && !isLoading) {
      startSession();
    }
  }, [stage, session, isLoading, startSession]);

  return (
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
              <Button size="lg" className="h-14 px-8 text-lg font-semibold bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400 text-white rounded-full shadow-lg shadow-purple-500/25">
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
            />
            <ActionFeed actions={actions} />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
