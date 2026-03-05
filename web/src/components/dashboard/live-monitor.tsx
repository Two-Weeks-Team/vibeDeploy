"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Wifi, WifiOff, Activity, Clock, Brain, Target, Play } from "lucide-react";
import { cn } from "@/lib/utils";
import { PipelineViz } from "./pipeline-viz";
import type { ActivePipeline, DashboardEvent, PipelineNodeStatus } from "@/types/dashboard";

interface LiveMonitorProps {
  activePipelines: ActivePipeline[];
  events: DashboardEvent[];
  nodeStatuses: Record<string, PipelineNodeStatus>;
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

export function LiveMonitor({ activePipelines, events, nodeStatuses, connected }: LiveMonitorProps) {
  const activePipeline = activePipelines[0];

  const getEventColor = (type: string) => {
    if (type.includes("error")) return "text-red-400";
    if (type.includes("complete")) return "text-emerald-400";
    if (type.includes("start")) return "text-blue-400";
    return "text-muted-foreground";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-500" />
          Live Monitor
        </h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Status:</span>
          {connected ? (
            <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
              <Wifi className="w-3 h-3 mr-1" /> Connected
            </Badge>
          ) : (
            <Badge className="bg-red-500/10 text-red-500 border-red-500/20">
              <WifiOff className="w-3 h-3 mr-1" /> Disconnected
            </Badge>
          )}
        </div>
      </div>

      {activePipelines.length === 0 ? (
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm py-12">
          <div className="flex flex-col items-center justify-center text-muted-foreground">
            <Play className="w-12 h-12 mb-4 opacity-20" />
            <p>No active pipelines</p>
            <p className="text-sm mt-2">Start an evaluation or brainstorm to see live activity</p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <motion.div variants={containerVariants} initial="hidden" animate="visible" className="space-y-4">
              <AnimatePresence mode="popLayout">
                {activePipelines.map((pipeline) => (
                  <motion.div key={pipeline.thread_id} variants={fadeUp} layout>
                    <Card className="border-blue-500/30 bg-blue-500/5 backdrop-blur-sm shadow-[0_0_15px_rgba(59,130,246,0.1)]">
                      <CardContent className="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                        <div className="flex items-center gap-4">
                          <div className="flex flex-col">
                            <div className="flex items-center gap-2 mb-1">
                              {pipeline.type === "evaluation" ? (
                                <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                                  <Target className="w-3 h-3 mr-1" /> Eval
                                </Badge>
                              ) : (
                                <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/20">
                                  <Brain className="w-3 h-3 mr-1" /> Brainstorm
                                </Badge>
                              )}
                              <span className="font-mono text-sm text-muted-foreground">
                                {pipeline.thread_id.substring(0, 8)}
                              </span>
                            </div>
                            <div className="text-sm font-medium truncate max-w-[300px]">
                              {pipeline.prompt_preview}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-6">
                          <div className="flex flex-col items-end">
                            <span className="text-xs text-muted-foreground mb-1">Phase</span>
                            <Badge variant="outline" className="capitalize">
                              {pipeline.phase}
                            </Badge>
                          </div>
                          <div className="flex flex-col items-end">
                            <span className="text-xs text-muted-foreground mb-1">Elapsed</span>
                            <div className="flex items-center gap-1 text-blue-400">
                              <Clock className="w-3 h-3" />
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

            {activePipeline && (
              <div className="mt-6">
                <h3 className="text-sm font-medium text-muted-foreground mb-4">Architecture View</h3>
                <PipelineViz
                  pipeline={activePipeline.type}
                  activeNodes={nodeStatuses}
                />
              </div>
            )}
          </div>

          <div className="lg:col-span-1">
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm h-full flex flex-col">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Activity className="w-4 h-4" /> Event Feed
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 p-0">
                <ScrollArea className="h-[600px] px-4 pb-4">
                  <div className="space-y-3">
                    <AnimatePresence initial={false}>
                      {events.map((event, i) => (
                        <motion.div
                          key={`${event.thread_id}-${event.type}-${event.node || 'none'}-${event.message?.substring(0, 10) || i}`}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="flex flex-col gap-1 text-sm border-l-2 border-border/50 pl-3 py-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className={cn("font-mono text-xs", getEventColor(event.type))}>
                              {event.type}
                            </span>
                            {event.node && (
                              <Badge variant="outline" className="text-[10px] h-4 px-1">
                                {event.node}
                              </Badge>
                            )}
                          </div>
                          {event.message && (
                            <span className="text-muted-foreground text-xs line-clamp-2">
                              {event.message}
                            </span>
                          )}
                        </motion.div>
                      ))}
                    </AnimatePresence>
                    {events.length === 0 && (
                      <div className="text-center text-muted-foreground text-sm py-8">
                        Waiting for events...
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
