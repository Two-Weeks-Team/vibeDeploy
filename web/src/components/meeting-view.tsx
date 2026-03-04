"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import confetti from "canvas-confetti";
import { CouncilMember } from "@/components/council-member";
import { CrossExam } from "@/components/cross-exam";
import { DecisionGate } from "@/components/decision-gate";
import { DeployStatus } from "@/components/deploy-status";
import { VibeScore } from "@/components/vibe-score";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { createSSEClient, type SSEEvent } from "@/lib/sse-client";

type AgentKey = "architect" | "scout" | "guardian" | "catalyst" | "advocate" | "strategist";

type AgentStatus = "idle" | "active" | "complete" | "error";

type AnalysisEntry = {
  agent: AgentKey;
  score: number;
  findingsCount: number;
};

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL ?? "http://localhost:8080";

const PHASES = ["Input", "Analysis", "Debate", "Scoring", "Verdict", "Build", "Deploy"] as const;

const AGENTS: {
  key: AgentKey;
  name: string;
  role: string;
  emoji: string;
  color: "amber" | "blue" | "emerald" | "purple" | "rose" | "slate";
}[] = [
  { key: "architect", name: "Architect", role: "Technical Lead", emoji: "🏗️", color: "amber" },
  { key: "scout", name: "Scout", role: "Market Analyst", emoji: "🔭", color: "blue" },
  { key: "guardian", name: "Guardian", role: "Risk Assessor", emoji: "🛡️", color: "emerald" },
  { key: "catalyst", name: "Catalyst", role: "Innovation Officer", emoji: "⚡", color: "purple" },
  { key: "advocate", name: "Advocate", role: "UX Champion", emoji: "🎯", color: "rose" },
  { key: "strategist", name: "Strategist", role: "Session Lead", emoji: "🧭", color: "slate" },
];

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

export function MeetingView({ meetingId }: { meetingId: string }) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
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
    const stop = createSSEClient({
      url: `${AGENT_URL}/run`,
      body: {
        prompt: "Run the council meeting and stream all events.",
        config: { configurable: { thread_id: meetingId } },
      },
      onEvent: (event) => {
        setEvents((prev) => [...prev, event]);
        handleEvent(event);
      },
      onComplete: () => {
        setStreamCompleted(true);
        setPhaseIndex(6);
      },
      onError: (streamError) => setError(streamError.message),
    });

    return stop;
  }, [handleEvent, meetingId]);

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
            <p className="text-sm text-muted-foreground">{liveHeadline}</p>
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
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.28 }}
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
                        <p className="text-sm text-muted-foreground">Waiting for first agent analysis...</p>
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
                        const key = `${event.type}-${asString(event.data.message) ?? ""}-${asString(event.data.node) ?? ""}-${asString(event.data.phase) ?? ""}-${asNumber(event.data.final_score) ?? 0}`;

                        return (
                        <div key={key} className="rounded-md border border-white/10 px-2 py-1">
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
            className={`rounded-lg border px-3 py-2 text-center text-xs ${
              active
                ? "border-primary/40 bg-primary/15 text-primary"
                : done
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
                  : "border-white/10 bg-card/40 text-muted-foreground"
            }`}
            animate={active ? { y: [0, -2, 0] } : { y: 0 }}
            transition={{ repeat: active ? Infinity : 0, duration: 1.4 }}
          >
            {phase}
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

function toAgentKey(value: string | undefined): AgentKey | null {
  if (!value) return null;
  const normalized = value.toLowerCase();
  if (normalized.includes("architect")) return "architect";
  if (normalized.includes("scout")) return "scout";
  if (normalized.includes("guardian")) return "guardian";
  if (normalized.includes("catalyst")) return "catalyst";
  if (normalized.includes("advocate")) return "advocate";
  if (normalized.includes("strategist")) return "strategist";
  return null;
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
