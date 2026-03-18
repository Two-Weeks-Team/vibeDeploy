"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Wifi, WifiOff, Activity, Clock, Brain, Target, Play, Workflow, Radio } from "lucide-react";
import { cn } from "@/lib/utils";
import { PipelineViz } from "./pipeline-viz";
import type { ActivePipeline, DashboardEvent, NodeMetadata, PipelineNodeStatus } from "@/types/dashboard";

interface LiveMonitorProps {
  activePipelines: ActivePipeline[];
  events: DashboardEvent[];
  nodeStatuses: Record<string, PipelineNodeStatus>;
  nodeMetadata?: Record<string, NodeMetadata>;
  connected: boolean;
}

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } },
};

function Elapsed({ ts }: { ts?: number }) {
  const [secs, setSecs] = useState(0);

  useEffect(() => {
    if (!ts) return;
    const update = () => setSecs(Math.max(0, Math.round((Date.now() - ts) / 1000)));
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [ts]);

  if (!ts) return null;
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return <span className="text-xs tabular-nums text-muted-foreground">{m > 0 ? `${m}m ${s.toString().padStart(2, "0")}s` : `${s}s`}</span>;
}

function ElapsedTime({ startedAt }: { startedAt: number }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const update = () => setElapsed(Math.floor((Date.now() - startedAt * 1000) / 1000));
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  return (
    <span className="font-mono text-sm">
      {mins.toString().padStart(2, "0")}:{secs.toString().padStart(2, "0")}
    </span>
  );
}

function EventFeed({ events }: { events: DashboardEvent[] }) {
  const getEventColor = (type: string) => {
    if (type.includes("error")) return "text-red-400";
    if (type.includes("complete")) return "text-emerald-400";
    if (type.includes("start")) return "text-blue-400";
    return "text-muted-foreground";
  };

  return (
    <Card className="flex h-full flex-col border-border/50 bg-card/50 backdrop-blur-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Activity className="h-4 w-4" /> Event Feed
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 p-0">
        <ScrollArea className="h-[280px] px-4 pb-4 md:h-[420px] xl:h-[640px]">
          <div className="space-y-3">
            <AnimatePresence initial={false}>
              {events.map((event, index) => (
                <motion.div
                  key={String(event._uid ?? `fallback-${event.thread_id}-${event.type}-${index}`)}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex flex-col gap-1 border-l-2 border-border/50 pl-3 py-1 text-sm"
                >
                  <div className="flex items-center justify-between gap-1">
                    <span className={cn("truncate font-mono text-xs", getEventColor(event.type))}>
                      {event.type}
                    </span>
                    <div className="flex shrink-0 items-center gap-1">
                      {event.node && (
                        <Badge variant="outline" className="h-4 px-1 text-[10px]">
                          {event.node}
                        </Badge>
                      )}
                      {event.axis && !event.node && (
                        <Badge variant="outline" className="h-4 px-1 text-[10px]">
                          {String(event.axis)}
                        </Badge>
                      )}
                      {event.agent && !event.node && (
                        <Badge variant="outline" className="h-4 px-1 text-[10px]">
                          {String(event.agent)}
                        </Badge>
                      )}
                      <Elapsed ts={event._timestamp as number | undefined} />
                    </div>
                  </div>
                  {event.message && <span className="line-clamp-2 text-xs text-muted-foreground">{event.message}</span>}
                </motion.div>
              ))}
            </AnimatePresence>
            {events.length === 0 && (
              <div className="py-8 text-center text-sm text-muted-foreground">
                Waiting for events...
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

export function LiveMonitor({ activePipelines, events, nodeStatuses, nodeMetadata, connected }: LiveMonitorProps) {
  const activePipeline = activePipelines[0];
  const latestEvent = events[0];

  const statusCards = useMemo(
    () => [
      {
        label: "Socket",
        value: connected ? "Connected" : "Reconnecting",
        icon: connected ? Wifi : WifiOff,
        className: connected ? "text-emerald-300" : "text-red-300",
      },
      {
        label: "Active",
        value: `${activePipelines.length}`,
        icon: Workflow,
        className: "text-blue-200",
      },
      {
        label: "Buffered events",
        value: `${events.length}`,
        icon: Radio,
        className: "text-cyan-200",
      },
      {
        label: "Latest event",
        value: latestEvent?.type ?? "Idle",
        icon: Clock,
        className: "text-slate-200",
      },
    ],
    [activePipelines.length, connected, events.length, latestEvent?.type],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Activity className="h-5 w-5 text-blue-500" />
          Live Monitor
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted-foreground">Status:</span>
          {connected ? (
            <Badge className="border-emerald-500/20 bg-emerald-500/10 text-emerald-500">
              <Wifi className="mr-1 h-3 w-3" /> Connected
            </Badge>
          ) : (
            <Badge className="border-red-500/20 bg-red-500/10 text-red-500">
              <WifiOff className="mr-1 h-3 w-3" /> Disconnected
            </Badge>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {activePipeline ? (
            <>
              <motion.div variants={containerVariants} initial="hidden" animate="visible" className="space-y-4">
                <AnimatePresence mode="popLayout">
                  {activePipelines.map((pipeline) => (
                    <motion.div key={pipeline.thread_id} variants={fadeUp} layout>
                      <Card className="border-blue-500/30 bg-blue-500/5 shadow-[0_0_15px_rgba(59,130,246,0.1)] backdrop-blur-sm">
                        <CardContent className="flex flex-col items-start justify-between gap-4 p-4 sm:flex-row sm:items-center">
                          <div className="flex items-center gap-4">
                            <div className="flex flex-col">
                              <div className="mb-1 flex items-center gap-2">
                                {pipeline.type === "evaluation" ? (
                                  <Badge className="border-blue-500/20 bg-blue-500/10 text-blue-400">
                                    <Target className="mr-1 h-3 w-3" /> Eval
                                  </Badge>
                                ) : (
                                  <Badge className="border-purple-500/20 bg-purple-500/10 text-purple-400">
                                    <Brain className="mr-1 h-3 w-3" /> Brainstorm
                                  </Badge>
                                )}
                                <span className="font-mono text-sm text-muted-foreground">
                                  {pipeline.thread_id.substring(0, 8)}
                                </span>
                              </div>
                              <div className="max-w-[420px] text-sm font-medium">
                                {pipeline.prompt_preview}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-6">
                            <div className="flex flex-col items-end">
                              <span className="mb-1 text-xs text-muted-foreground">Phase</span>
                              <Badge variant="outline" className="capitalize">
                                {pipeline.phase}
                              </Badge>
                            </div>
                            <div className="flex flex-col items-end">
                              <span className="mb-1 text-xs text-muted-foreground">Elapsed</span>
                              <div className="flex items-center gap-1 text-blue-400">
                                <Clock className="h-3 w-3" />
                                <ElapsedTime startedAt={pipeline.started_at} />
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </motion.div>

              <div className="space-y-3">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Architecture View</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Live node states align to the exact named steps now in flight, including the five council agents, the five score axes, prompt strategy, CI, build, deploy, and live verification.
                  </p>
                </div>
                <PipelineViz pipeline={activePipeline.type} activeNodes={nodeStatuses} nodeMetadata={nodeMetadata} />
              </div>
            </>
          ) : (
            <>
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Play className="h-4 w-4 text-blue-400" />
                    Ready For The Next Run
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                    {statusCards.map((item) => {
                      const Icon = item.icon;
                      return (
                        <div
                          key={item.label}
                          className="rounded-2xl border border-border/50 bg-background/40 p-4"
                        >
                          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                            <Icon className="h-3.5 w-3.5" />
                            {item.label}
                          </div>
                          <div className={cn("text-sm font-medium", item.className)}>{item.value}</div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="rounded-2xl border border-border/50 bg-background/30 p-4 text-sm text-muted-foreground">
                    No pipeline is active right now. The stream is still attached, recent events remain visible, and the preview below shows the exact path the next evaluation will traverse when a run starts.
                  </div>
                </CardContent>
              </Card>

              <div className="space-y-3">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Architecture Preview</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    The preview keeps every named step visible from Input Processor through Verified Live so the next run can be traced without hidden stages.
                  </p>
                </div>
                <PipelineViz pipeline="evaluation" className="h-[780px] lg:h-[820px]" />
              </div>
            </>
          )}
        </div>

        <div className="lg:col-span-1">
          <EventFeed events={events} />
        </div>
      </div>
    </div>
  );
}
