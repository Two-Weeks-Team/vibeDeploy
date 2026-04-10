"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { DASHBOARD_API_URL, getBrainstormResult, type BrainstormResult } from "@/lib/api";
import { createSSEClient, type SSEEvent } from "@/lib/sse-client";
import { cn } from "@/lib/utils";
import { AGENT_MAP, type AgentKey, toAgentKey } from "@/config/agents";

type PhaseStep = {
  key: string;
  label: string;
  status: "pending" | "active" | "complete";
};

type AgentInsight = {
  agent: string;
  ideas: Array<{ title: string; description: string }>;
  opportunities: string[];
  wild_card: string;
  action_items: string[];
};

export function BrainstormView({ sessionId }: { sessionId: string }) {
  const [phases, setPhases] = useState<PhaseStep[]>([
    { key: "input_processor", label: "Analyzing your idea...", status: "pending" },
    { key: "run_brainstorm_agent", label: "Agents brainstorming...", status: "pending" },
    { key: "synthesize_brainstorm", label: "Synthesizing insights...", status: "pending" },
  ]);
  const [insights, setInsights] = useState<AgentInsight[]>([]);
  const [result, setResult] = useState<BrainstormResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [streamCompleted, setStreamCompleted] = useState(false);

  const updatePhase = useCallback((key: string, status: "active" | "complete") => {
    setPhases((prev) =>
      prev.map((p) => (p.key === key ? { ...p, status } : p)),
    );
  }, []);

  const handleEvent = useCallback(
    (event: SSEEvent) => {
      const payload = event.data;

      if (event.type === "brainstorm.node.start") {
        const node = asString(payload.node);
        if (node) updatePhase(node, "active");
        return;
      }

      if (event.type === "brainstorm.node.complete") {
        const node = asString(payload.node);
        if (node) updatePhase(node, "complete");
        return;
      }

      if (event.type === "brainstorm.agent.insight") {
        const insight = payload as unknown as AgentInsight;
        if (insight.agent) {
          setInsights((prev) => {
            const exists = prev.find((i) => i.agent === insight.agent);
            if (exists) return prev;
            return [...prev, insight];
          });
        }
        return;
      }

      if (event.type === "brainstorm.phase.complete") {
        setStreamCompleted(true);
        getBrainstormResult(sessionId).then((res) => {
          if (res) setResult(res);
        });
        return;
      }

      if (event.type === "brainstorm.error") {
        setError(asString(payload.error) ?? "Brainstorm streaming failed.");
        return;
      }
    },
    [sessionId, updatePhase],
  );

  useEffect(() => {
    let stopFn: (() => void) | undefined;
    let cancelled = false;

    // Check if result already exists (page refresh case)
    getBrainstormResult(sessionId).then((existing) => {
      if (cancelled) return;
      if (existing) {
        setResult(existing);
        setStreamCompleted(true);
        return;
      }

      stopFn = createSSEClient({
        url: `${DASHBOARD_API_URL}/brainstorm`,
        body: {
          prompt: "Run brainstorm and stream all events.",
          config: { configurable: { thread_id: sessionId } },
        },
        onEvent: handleEvent,
        onComplete: () => {
          setStreamCompleted(true);
          getBrainstormResult(sessionId).then((res) => {
            if (res) setResult(res);
          });
        },
        onError: (err) => setError(err.message),
      });
    }).catch(() => {
      if (cancelled) return;
      stopFn = createSSEClient({
        url: `${DASHBOARD_API_URL}/brainstorm`,
        body: {
          prompt: "Run brainstorm and stream all events.",
          config: { configurable: { thread_id: sessionId } },
        },
        onEvent: handleEvent,
        onComplete: () => {
          setStreamCompleted(true);
          getBrainstormResult(sessionId).then((res) => {
            if (res) setResult(res);
          });
        },
        onError: (err) => setError(err.message),
      });
    });

    return () => {
      cancelled = true;
      stopFn?.();
    };
  }, [handleEvent, sessionId]);

  const synthesis = result?.synthesis;
  const displayInsights = result?.insights ?? insights;

  const currentPhaseLabel = useMemo(() => {
    const active = phases.find((p) => p.status === "active");
    if (active) return active.label;
    if (streamCompleted) return "Brainstorm complete";
    return "Preparing...";
  }, [phases, streamCompleted]);

  return (
    <div className="space-y-6">
      <ProgressBar phases={phases} />

      <Card className="border-white/10 bg-card/50">
        <CardContent className="flex items-center justify-between gap-3 p-4">
          <div className="flex items-center gap-2">
            {!streamCompleted && (
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-purple-400/75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-purple-400" />
              </span>
            )}
            <p className="text-sm text-muted-foreground">{currentPhaseLabel}</p>
          </div>
          <Badge variant="secondary" className="text-xs">
            {streamCompleted ? "Complete" : "Live"}
          </Badge>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result?.idea_summary && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Card className="border-purple-500/20 bg-gradient-to-br from-purple-500/10 via-transparent to-amber-500/10">
            <CardContent className="p-4">
              <p className="text-sm font-medium text-muted-foreground">Idea Summary</p>
              <p className="mt-1 text-base leading-relaxed">{result.idea_summary}</p>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {displayInsights.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <AnimatePresence>
            {displayInsights.map((insight, index) => {
              const agentKey = toAgentKey(insight.agent);
              const agent = agentKey ? AGENT_MAP[agentKey] : null;
              return (
                <motion.div
                  key={insight.agent}
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.35, delay: index * 0.1 }}
                >
                  <Card
                    className={cn(
                      "h-full border-white/10 bg-gradient-to-br",
                      agent?.gradient ?? "from-slate-500/20 to-slate-600/5",
                    )}
                  >
                    <CardHeader className="pb-3">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <span
                          className={cn(
                            "flex h-9 w-9 items-center justify-center rounded-lg border text-lg",
                            agent?.color ?? "border-slate-400/40 bg-slate-500/10",
                          )}
                        >
                          {agent?.emoji ?? "?"}
                        </span>
                        <div>
                          <p className="text-sm font-semibold">
                            {agent?.name ?? insight.agent}
                          </p>
                        </div>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3 pt-0">
                      {insight.ideas.length > 0 && (
                        <div>
                          <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                            Ideas
                          </p>
                          <div className="space-y-2">
                            {insight.ideas.map((idea) => (
                              <div
                                key={idea.title}
                                className="rounded-lg border border-white/10 bg-muted/20 p-2"
                              >
                                <p className="text-xs font-semibold">{idea.title}</p>
                                <p className="mt-0.5 text-xs text-muted-foreground">
                                  {idea.description}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {insight.opportunities.length > 0 && (
                        <div>
                          <p className="mb-1 text-xs font-medium text-muted-foreground">
                            Opportunities
                          </p>
                          <ul className="space-y-1">
                            {insight.opportunities.map((opp) => (
                              <li
                                key={opp}
                                className="text-xs text-muted-foreground"
                              >
                                <span className="mr-1 text-emerald-400">+</span>
                                {opp}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {insight.wild_card && (
                        <motion.div
                          initial={{ scale: 0.9 }}
                          animate={{ scale: 1 }}
                          transition={{ type: "spring", stiffness: 300, damping: 20 }}
                          className="rounded-lg border border-amber-400/30 bg-amber-500/10 p-2"
                        >
                          <p className="text-xs font-medium text-amber-300">
                            Wild Card
                          </p>
                          <p className="mt-0.5 text-xs text-amber-200/80">
                            {insight.wild_card}
                          </p>
                        </motion.div>
                      )}

                      {insight.action_items.length > 0 && (
                        <div>
                          <p className="mb-1 text-xs font-medium text-muted-foreground">
                            Action Items
                          </p>
                          <ul className="space-y-1">
                            {insight.action_items.map((item) => (
                              <li
                                key={item}
                                className="flex items-start gap-1.5 text-xs text-muted-foreground"
                              >
                                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/60" />
                                {item}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      ) : (
        !streamCompleted &&
        !error && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {["skel-architect", "skel-scout", "skel-guardian", "skel-catalyst", "skel-advocate"].map((id) => (
              <Card key={id} className="border-white/10 bg-card/50">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-9 w-9 rounded-lg" />
                    <Skeleton className="h-4 w-24" />
                  </div>
                </CardHeader>
                <CardContent className="space-y-2 pt-0">
                  <Skeleton className="h-16 w-full rounded-lg" />
                  <Skeleton className="h-3 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </CardContent>
              </Card>
            ))}
          </div>
        )
      )}

      {synthesis && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.2 }}
          className="space-y-5"
        >
          <h2 className="text-xl font-bold tracking-tight">Synthesis</h2>

          {synthesis.themes.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {synthesis.themes.map((theme) => (
                <Badge
                  key={theme}
                  variant="secondary"
                  className="bg-purple-500/15 text-purple-200"
                >
                  {theme}
                </Badge>
              ))}
            </div>
          )}

          {synthesis.recommended_direction && (
            <Card className="border-purple-500/30 bg-gradient-to-r from-purple-500/15 to-transparent">
              <CardContent className="p-4">
                <p className="text-xs font-medium text-purple-300">
                  Recommended Direction
                </p>
                <p className="mt-1 text-sm leading-relaxed">
                  {synthesis.recommended_direction}
                </p>
              </CardContent>
            </Card>
          )}

          {synthesis.top_ideas.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
                Top Ideas
              </h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {synthesis.top_ideas.map((idea, idx) => {
                  const sourceKey = toAgentKey(idea.source_agent);
                  const sourceAgent = sourceKey ? AGENT_MAP[sourceKey] : null;
                  return (
                    <motion.div
                      key={idea.title}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.08 }}
                    >
                      <Card className="h-full border-white/10 bg-muted/20">
                        <CardContent className="p-3">
                          <div className="mb-2 flex items-center justify-between">
                            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/20 text-xs font-bold text-primary">
                              {idx + 1}
                            </span>
                            {sourceAgent && (
                              <span className="text-xs text-muted-foreground">
                                {sourceAgent.emoji} {sourceAgent.name}
                              </span>
                            )}
                          </div>
                          <p className="text-sm font-semibold">{idea.title}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {idea.description}
                          </p>
                        </CardContent>
                      </Card>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          )}

          {synthesis.synergies.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
                Synergies
              </h3>
              <div className="grid gap-2 sm:grid-cols-2">
                {synthesis.synergies.map((synergy) => (
                  <div
                    key={synergy}
                    className="flex items-start gap-2 rounded-lg border border-white/10 bg-muted/20 p-3"
                  >
                    <span className="mt-0.5 text-xs text-emerald-400">
                      &harr;
                    </span>
                    <p className="text-xs text-muted-foreground">{synergy}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {synthesis.quick_wins.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
                Quick Wins
              </h3>
              <ul className="space-y-2">
                {synthesis.quick_wins.map((win) => (
                  <li
                    key={win}
                    className="flex items-start gap-2 rounded-lg border border-white/10 bg-muted/20 p-3"
                  >
                    <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border border-emerald-400/40 text-[10px] text-emerald-400">
                      &#x2713;
                    </span>
                    <p className="text-xs text-muted-foreground">{win}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}

function ProgressBar({ phases }: { phases: PhaseStep[] }) {
  return (
    <div className="grid gap-2 sm:grid-cols-3">
      {phases.map((phase) => (
        <motion.div
          key={phase.key}
          layout
          className={cn(
            "rounded-lg border px-3 py-2 text-center text-xs font-medium",
            phase.status === "active" &&
              "border-purple-400/40 bg-purple-500/15 text-purple-300 shadow-[0_0_12px_rgba(168,85,247,0.15)]",
            phase.status === "complete" &&
              "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
            phase.status === "pending" &&
              "border-white/10 bg-card/40 text-muted-foreground",
          )}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={
            phase.status === "active"
              ? { opacity: 1, scale: 1, y: [0, -2, 0] }
              : { opacity: 1, scale: 1, y: 0 }
          }
          transition={
            phase.status === "active"
              ? { y: { repeat: Infinity, duration: 1.4 }, opacity: { duration: 0.3 } }
              : { duration: 0.3 }
          }
        >
          <span className="flex items-center justify-center gap-1">
            {phase.status === "complete" && (
              <span className="text-emerald-400">&#x2713;</span>
            )}
            {phase.label}
          </span>
        </motion.div>
      ))}
    </div>
  );
}

function asString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}
