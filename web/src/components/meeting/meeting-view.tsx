"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import confetti from "canvas-confetti";
import { CouncilMember } from "@/components/meeting/council-member";
import { CrossExam } from "@/components/meeting/cross-exam";
import { DecisionGate } from "@/components/meeting/decision-gate";
import { DeployStatus } from "@/components/result/deploy-status";
import { VibeScore } from "@/components/result/vibe-score";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { DASHBOARD_API_URL, resumeMeeting } from "@/lib/api";
import { createSSEClient, type SSEEvent } from "@/lib/sse-client";
import { AGENTS, type AgentKey, toAgentKey } from "@/config/agents";

type AgentStatus = "idle" | "active" | "complete" | "error";

type AnalysisEntry = {
  agent: AgentKey;
  score: number;
  findingsCount: number;
};

const PHASES = ["Input", "Analysis", "Debate", "Scoring", "Verdict", "Build", "Deploy"] as const;

const phaseToIndex: Record<string, number> = {
  input: 0,
  analysis: 1,
  debate: 2,
  scoring: 3,
  verdict: 4,
  build: 5,
  deploy: 6,
  complete: 6,
};

type SSEEventWithId = SSEEvent & { _uid: string };

export function MeetingView({ meetingId }: { meetingId: string }) {
  const router = useRouter();
  const [events, setEvents] = useState<SSEEventWithId[]>([]);
  const eventSeq = useRef(0);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [agentStatus, setAgentStatus] = useState<Record<AgentKey, AgentStatus>>({
    architect: "idle",
    scout: "idle",
    guardian: "idle",
    catalyst: "idle",
    advocate: "idle",
    strategist: "idle",
  });
  const [messages, setMessages] = useState<Record<AgentKey, string>>({
    architect: "",
    scout: "",
    guardian: "",
    catalyst: "",
    advocate: "",
    strategist: "",
  });
  const [analyses, setAnalyses] = useState<AnalysisEntry[]>([]);
  const [debates, setDebates] = useState<{ from: string; to: string; argument: string; response?: string }[]>([]);
  const [verdict, setVerdict] = useState<{ score: number; decision: "GO" | "CONDITIONAL" | "NO_GO" } | null>(null);
  const [deploy, setDeploy] = useState<{ liveUrl?: string; repoUrl?: string; failed?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [streamCompleted, setStreamCompleted] = useState(false);

  const handleEvent = useCallback((event: SSEEvent) => {
    const payload = event.data;

    if (event.type === "council.phase.start") {
      const phase = asString(payload.phase)?.toLowerCase();
      if (phase && phase in phaseToIndex) setPhaseIndex(phaseToIndex[phase]);
      return;
    }

    if (event.type === "council.node.start") {
      const agent = toAgentKey(asString(payload.node));
      const phase = asString(payload.phase)?.toLowerCase();
      const message = asString(payload.message) ?? "Analyzing the idea.";
      if (phase && phase in phaseToIndex) setPhaseIndex(phaseToIndex[phase]);
      if (agent) {
        setAgentStatus((prev) => ({ ...prev, [agent]: "active" }));
        setMessages((prev) => ({ ...prev, [agent]: message }));
      }
      if (phase === "debate") {
        setDebates((prev) => [...prev, { from: mapNodeLabel(agent), to: "Council", argument: message }]);
      }
      return;
    }

    if (event.type === "council.node.complete") {
      const agent = toAgentKey(asString(payload.node));
      const message = asString(payload.message);
      if (agent) {
        setAgentStatus((prev) => ({ ...prev, [agent]: "complete" }));
        if (message) setMessages((prev) => ({ ...prev, [agent]: message }));
      }
      return;
    }

    if (event.type === "council.agent.analysis") {
      const agent = toAgentKey(asString(payload.agent));
      if (!agent) return;

      const score = asNumber(payload.score) ?? 0;
      const findingsCount = asNumber(payload.findings_count) ?? 0;

      setAnalyses((prev) => {
        const next = prev.filter((item) => item.agent !== agent);
        next.push({ agent, score, findingsCount });
        return next;
      });
      setAgentStatus((prev) => ({ ...prev, [agent]: "complete" }));
      setPhaseIndex(3);
      return;
    }

    if (event.type === "council.verdict") {
      const finalScore = asNumber(payload.final_score) ?? 0;
      const decision = asVerdict(asString(payload.decision));
      setVerdict({ score: finalScore, decision });
      setPhaseIndex(4);
      return;
    }

    if (event.type === "deploy.complete") {
      setDeploy({
        liveUrl: asString(payload.live_url),
        repoUrl: asString(payload.github_repo),
      });
      setPhaseIndex(6);
      return;
    }

    if (event.type === "council.phase.complete") {
      const phase = asString(payload.phase)?.toLowerCase();
      if (phase === "complete") {
        setStreamCompleted(true);
        setPhaseIndex(6);
      }
      return;
    }

    if (event.type === "council.error") {
      setError(asString(payload.error) ?? "Council streaming failed.");
      setDeploy((prev) => ({ ...prev, failed: asString(payload.error) ?? "Unknown error" }));
      return;
    }
  }, []);

  useEffect(() => {
    let stopFn: (() => void) | undefined;
    let cancelled = false;

    (async () => {
      // Check if result already exists (page refresh case)
      try {
        const { getMeetingResult } = await import("@/lib/api");
        const existing = await getMeetingResult(meetingId);
        if (existing && !cancelled) {
          router.push(`/result/${meetingId}`);
          return;
        }
      } catch {
        // Result not found — proceed with new stream
      }

      if (cancelled) return;

      stopFn = createSSEClient({
        url: `${DASHBOARD_API_URL}/run`,
        body: {
          prompt: "Run the council meeting and stream all events.",
          config: { configurable: { thread_id: meetingId } },
        },
        onEvent: (event) => {
          const tagged = { ...event, _uid: `mev-${++eventSeq.current}` };
          setEvents((prev) => [...prev, tagged]);
          handleEvent(event);
        },
        onComplete: () => {
          setStreamCompleted(true);
          setPhaseIndex(6);
          setTimeout(() => router.push(`/result/${meetingId}`), 2000);
        },
        onError: (streamError) => setError(streamError.message),
      });
    })();

    return () => {
      cancelled = true;
      stopFn?.();
    };
  }, [handleEvent, meetingId, router]);

  useEffect(() => {
    if (verdict?.decision !== "GO") return;
    confetti({
      particleCount: 120,
      spread: 70,
      origin: { y: 0.28 },
    });
  }, [verdict?.decision]);

  const liveHeadline = useMemo(() => {
    const last = events[events.length - 1];
    const message = asString(last?.data.message);
    return message || "Council convened. Streaming updates...";
  }, [events]);

  return (
    <div className="space-y-5">
      <div className="space-y-3">
        <PhaseStepper phaseIndex={phaseIndex} />
        <Card className="border-white/10 bg-card/50">
          <CardContent className="flex items-center justify-between gap-3 p-4">
            <div className="flex items-center gap-2">
              {!streamCompleted && (
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
                </span>
              )}
              <p className="text-sm text-muted-foreground">{liveHeadline}</p>
            </div>
            <Badge variant="secondary" className="text-xs">
              {streamCompleted ? "Complete" : "Live"}
            </Badge>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <aside className="space-y-3">
          {AGENTS.map((agent) => (
            <CouncilMember
              key={agent.key}
              name={agent.name}
              role={agent.role}
              emoji={agent.emoji}
              color={agent.color}
              status={error ? "error" : agentStatus[agent.key]}
              isSpeaking={agentStatus[agent.key] === "active"}
              message={messages[agent.key]}
              score={analyses.find((item) => item.agent === agent.key)?.score}
            />
          ))}
        </aside>

        <main>
          <AnimatePresence mode="wait">
            <motion.div
              key={phaseIndex}
              initial={{ opacity: 0, y: 16, filter: "blur(4px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -12, filter: "blur(4px)" }}
              transition={{ duration: 0.35, ease: "easeOut" as const }}
              className="space-y-4"
            >
              {phaseIndex <= 1 && (
                <Card className="border-white/10 bg-gradient-to-br from-blue-500/10 via-transparent to-emerald-500/10">
                  <CardHeader>
                    <CardTitle>Analysis Stream</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-3 md:grid-cols-2">
                      {analyses.length === 0 ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span className="flex gap-0.5">
                            {[0, 1, 2].map((i) => (
                              <motion.span
                                key={i}
                                className="h-1.5 w-1.5 rounded-full bg-primary/60"
                                animate={{ opacity: [0.3, 1, 0.3] }}
                                transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                              />
                            ))}
                          </span>
                          Agents are analyzing the idea...
                        </div>
                      ) : (
                        analyses.map((item, index) => (
                          <motion.div
                            key={item.agent}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.08 }}
                            className="rounded-xl border border-white/10 bg-muted/20 p-3"
                          >
                            <p className="text-sm font-medium capitalize">{item.agent}</p>
                            <p className="text-xs text-muted-foreground">Findings: {item.findingsCount}</p>
                            <p className="mt-1 text-lg font-semibold">{Math.round(item.score)}/100</p>
                          </motion.div>
                        ))
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {phaseIndex === 2 && <CrossExam exchanges={debates} />}

              {phaseIndex === 3 && (
                <VibeScore
                  score={averageScore(analyses)}
                  breakdown={{
                    tech: scoreByAgent(analyses, "architect"),
                    market: scoreByAgent(analyses, "scout"),
                    innovation: scoreByAgent(analyses, "catalyst"),
                    risk: scoreByAgent(analyses, "guardian"),
                    userImpact: scoreByAgent(analyses, "advocate"),
                  }}
                />
              )}

              {phaseIndex >= 4 && verdict && (
                <motion.div
                  animate={verdict.decision === "NO_GO" ? { x: [0, -6, 6, -4, 4, 0] } : { x: 0 }}
                  transition={{ duration: 0.45 }}
                >
                  <DecisionGate
                    verdict={verdict.decision === "NO_GO" ? "NO-GO" : verdict.decision}
                    score={verdict.score}
                    onProceed={() => resumeMeeting(meetingId, "deploy")}
                    suggestions={
                      verdict.decision === "CONDITIONAL"
                        ? [
                            "Reduce MVP scope to one user workflow.",
                            "Ship a read-only first release, then add automation.",
                          ]
                        : verdict.decision === "NO_GO"
                          ? [
                              "Refocus on one validated use-case.",
                              "Cut operational complexity before launch.",
                            ]
                          : ["All dimensions cleared. Proceed to build + deploy."]
                    }
                    onRevise={() => router.push("/")}
                  />
                </motion.div>
              )}

              {phaseIndex >= 5 && (
                <DeployStatus
                  currentStep={
                    deploy.failed
                      ? "failed"
                      : deploy.liveUrl
                        ? "live"
                        : phaseIndex === 5
                          ? "deploy"
                          : "push"
                  }
                  repoUrl={deploy.repoUrl}
                  liveUrl={deploy.liveUrl}
                  error={deploy.failed}
                />
              )}

              <Card className="border-white/10 bg-card/50">
                <CardHeader>
                  <CardTitle className="text-sm">Event Timeline</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-40 pr-4">
                    <div className="space-y-2 text-xs">
                      {events.slice(-20).map((event) => {
                        return (
                        <div key={event._uid} className="rounded-md border border-white/10 px-2 py-1">
                          <span className="font-medium">{event.type}</span>
                          <span className="ml-2 text-muted-foreground">{asString(event.data.message) ?? "event"}</span>
                        </div>
                        );
                      })}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

function PhaseStepper({ phaseIndex }: { phaseIndex: number }) {
  return (
    <div className="grid gap-2 sm:grid-cols-7">
      {PHASES.map((phase, index) => {
        const active = index === phaseIndex;
        const done = index < phaseIndex;

        return (
          <motion.div
            key={phase}
            layout
            className={`rounded-lg border px-3 py-2 text-center text-xs font-medium ${
              active
                ? "border-primary/40 bg-primary/15 text-primary shadow-[0_0_12px_rgba(99,102,241,0.15)]"
                : done
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : "border-white/10 bg-card/40 text-muted-foreground"
            }`}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={active ? { opacity: 1, scale: 1, y: [0, -2, 0] } : { opacity: 1, scale: 1, y: 0 }}
            transition={active ? { y: { repeat: Infinity, duration: 1.4 }, opacity: { duration: 0.3 } } : { duration: 0.3 }}
          >
            <span className="flex items-center justify-center gap-1">
              {done && <span className="text-emerald-400">✓</span>}
              {phase}
            </span>
          </motion.div>
        );
      })}
    </div>
  );
}

function asString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function asNumber(value: unknown): number | undefined {
  return typeof value === "number" ? value : undefined;
}

function asVerdict(value: string | undefined): "GO" | "CONDITIONAL" | "NO_GO" {
  if (value === "GO") return "GO";
  if (value === "CONDITIONAL") return "CONDITIONAL";
  return "NO_GO";
}

function mapNodeLabel(agent: AgentKey | null): string {
  if (!agent) return "Council";
  return agent.charAt(0).toUpperCase() + agent.slice(1);
}

function averageScore(entries: AnalysisEntry[]): number {
  if (entries.length === 0) return 0;
  const total = entries.reduce((acc, entry) => acc + entry.score, 0);
  return Math.round(total / entries.length);
}

function scoreByAgent(entries: AnalysisEntry[], agent: AgentKey): number {
  return entries.find((entry) => entry.agent === agent)?.score ?? 0;
}
