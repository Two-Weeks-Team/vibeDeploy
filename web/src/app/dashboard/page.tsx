"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Activity, Target, Brain, CheckCircle, XCircle, Zap, TrendingUp, RadioTower, RefreshCw } from "lucide-react";
import { useDashboard } from "@/hooks/use-dashboard";
import { usePipelineMonitor } from "@/hooks/use-pipeline-monitor";
import { PipelineViz } from "@/components/dashboard/pipeline-viz";
import { DashboardCharts } from "@/components/dashboard/dashboard-charts";
import { HistoryList } from "@/components/dashboard/history-list";
import { LiveMonitor } from "@/components/dashboard/live-monitor";
import { DeployedApps } from "@/components/dashboard/deployed-apps";
import type { VerdictType, MeetingResultFull, BrainstormResultFull } from "@/types/dashboard";

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } },
};

const VERDICT_COLORS = {
  GO: "#10b981",
  CONDITIONAL: "#f59e0b",
  "NO-GO": "#ef4444",
};

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState("overview");
  const {
    healthy,
    stats,
    results,
    brainstorms,
    deployments,
    loading,
    lastUpdated,
    scoreDistribution,
    verdictBreakdown,
    agentPerformance,
    scoreTrend,
  } = useDashboard();

  const { activePipelines, events, nodeStatuses, connected } = usePipelineMonitor();

  const highestScore = useMemo(() => {
    if (!results.length) return 0;
    return Math.max(...results.map((r) => r.score || 0));
  }, [results]);

  const recentActivity = useMemo(() => {
    const unified = [
      ...results.map((r) => ({ type: "evaluation" as const, data: r, date: new Date(r.created_at) })),
      ...brainstorms.map((b) => ({ type: "brainstorm" as const, data: b, date: new Date(b.created_at) })),
    ];
    return unified.sort((a, b) => b.date.getTime() - a.date.getTime()).slice(0, 5);
  }, [results, brainstorms]);

  const verdictData = Object.entries(verdictBreakdown).map(([name, value]) => ({
    name,
    value,
    fill: VERDICT_COLORS[name as VerdictType],
  }));
  const totalVerdicts = verdictData.reduce((sum, entry) => sum + entry.value, 0);
  const tabTriggerClass = "h-10 flex-none basis-[calc(50%-0.25rem)] sm:basis-[calc(33.333%-0.375rem)] lg:basis-0";

  if (loading) {
    return (
      <div className="min-h-screen bg-background text-foreground p-6">
        <div className="max-w-[1400px] mx-auto space-y-6">
          <div className="flex items-center justify-between">
            <Skeleton className="h-10 w-48" />
            <Skeleton className="h-10 w-32" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {["s1", "s2", "s3", "s4", "s5", "s6"].map((id) => (
              <Skeleton key={id} className="h-24 w-full" />
            ))}
          </div>
          <Skeleton className="h-[600px] w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground p-4 sm:p-6 lg:p-8">
      <div className="max-w-[1400px] mx-auto space-y-8">
        <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-muted-foreground hover:text-foreground transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight flex items-center gap-2">
                System Dashboard
                {healthy === true && (
                  <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 ml-2">
                    <Activity className="w-3 h-3 mr-1" /> Online
                  </Badge>
                )}
                {healthy === false && (
                  <Badge className="bg-red-500/10 text-red-500 border-red-500/20 ml-2">
                    <XCircle className="w-3 h-3 mr-1" /> Offline
                  </Badge>
                )}
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                Real-time monitoring and analytics for vibeDeploy
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="border-border/50 bg-background/40 text-foreground">
              <RadioTower className="mr-1 h-3 w-3" />
              Stream {connected ? "connected" : "reconnecting"}
            </Badge>
            <Badge variant="outline" className="border-border/50 bg-background/40 text-foreground">
              <Activity className="mr-1 h-3 w-3" />
              {activePipelines.length} active
            </Badge>
            <Badge variant="outline" className="border-border/50 bg-background/40 text-foreground">
              <RefreshCw className="mr-1 h-3 w-3" />
              {lastUpdated
                ? `Updated ${new Date(lastUpdated).toLocaleTimeString("en-US", {
                    hour: "numeric",
                    minute: "2-digit",
                    second: "2-digit",
                  })}`
                : "Waiting for sync"}
            </Badge>
          </div>
        </header>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="mb-8 h-auto w-full flex-wrap justify-start gap-2 p-1">
            <TabsTrigger value="overview" className={tabTriggerClass}>Overview</TabsTrigger>
            <TabsTrigger value="live" className={tabTriggerClass}>
              Live Monitor
              {activePipelines.length > 0 && (
                <span className="ml-2 flex h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
              )}
            </TabsTrigger>
            <TabsTrigger value="deployed" className={tabTriggerClass}>
              Deployed Apps
              {deployments.length > 0 && (
                <Badge variant="secondary" className="ml-2 bg-primary/20 text-primary hover:bg-primary/30">
                  {deployments.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="history" className={tabTriggerClass}>History</TabsTrigger>
            <TabsTrigger value="analytics" className={tabTriggerClass}>Analytics</TabsTrigger>
          </TabsList>

            <TabsContent value="overview" className="space-y-6 outline-none">
              <motion.div variants={containerVariants} initial="hidden" animate="visible" className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <motion.div variants={fadeUp}>
                  <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        <Target className="w-4 h-4 text-blue-400" /> Evaluations
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">{stats.total_meetings}</div>
                    </CardContent>
                  </Card>
                </motion.div>
                <motion.div variants={fadeUp}>
                  <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        <Brain className="w-4 h-4 text-purple-400" /> Brainstorms
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">{stats.total_brainstorms}</div>
                    </CardContent>
                  </Card>
                </motion.div>
                <motion.div variants={fadeUp}>
                  <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        <Activity className="w-4 h-4 text-yellow-400" /> Avg Score
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">{stats.avg_score.toFixed(1)}</div>
                    </CardContent>
                  </Card>
                </motion.div>
                <motion.div variants={fadeUp}>
                  <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-emerald-400" /> GO Count
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">{stats.go_count}</div>
                    </CardContent>
                  </Card>
                </motion.div>
                <motion.div variants={fadeUp}>
                  <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        <XCircle className="w-4 h-4 text-red-400" /> NO-GO Count
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">{stats.nogo_count}</div>
                    </CardContent>
                  </Card>
                </motion.div>
                <motion.div variants={fadeUp}>
                  <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-indigo-400" /> Highest Score
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">{highestScore.toFixed(1)}</div>
                    </CardContent>
                  </Card>
                </motion.div>
              </motion.div>

              <motion.div variants={fadeUp} initial="hidden" animate="visible">
                <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">Architecture Overview</h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                      One prompt fans into the council, routes through repair or GO, then runs all the way through code, CI, and live deployment.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline" className="border-blue-500/20 bg-blue-500/10 text-blue-200">Council</Badge>
                    <Badge variant="outline" className="border-orange-500/20 bg-orange-500/10 text-orange-200">Repair loop</Badge>
                    <Badge variant="outline" className="border-emerald-500/20 bg-emerald-500/10 text-emerald-200">GO route</Badge>
                    <Badge variant="outline" className="border-cyan-500/20 bg-cyan-500/10 text-cyan-200">Ship chain</Badge>
                  </div>
                </div>
                <PipelineViz pipeline="evaluation" />
              </motion.div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <motion.div variants={fadeUp} initial="hidden" animate="visible" className="lg:col-span-2">
                  <Card className="border-border/50 bg-card/50 backdrop-blur-sm h-full">
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Zap className="w-5 h-5 text-yellow-500" /> Recent Activity
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {recentActivity.length === 0 ? (
                          <div className="text-center text-muted-foreground py-8">No recent activity</div>
                        ) : (
                          recentActivity.map((item) => (
                            <div
                              key={item.type === "evaluation" ? item.data.thread_id : item.data.thread_id}
                              className="flex flex-col gap-3 rounded-lg bg-accent/50 p-3 sm:flex-row sm:items-center sm:justify-between"
                            >
                              <div className="flex min-w-0 items-center gap-3">
                                {item.type === "evaluation" ? (
                                  <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">Eval</Badge>
                                ) : (
                                  <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/20">Brainstorm</Badge>
                                )}
                                <span className="min-w-0 flex-1 truncate text-sm text-foreground sm:max-w-[300px]">
                                  {(item.type === "evaluation" ? (item.data as MeetingResultFull).idea_summary || (item.data as MeetingResultFull).input_prompt : (item.data as BrainstormResultFull).idea_summary) || item.data.thread_id}
                                </span>
                              </div>
                              <div className="flex w-full flex-wrap items-center justify-between gap-3 sm:w-auto sm:justify-end sm:gap-4">
                                {item.type === "evaluation" && (
                                  <>
                                    <span className="font-bold">{item.data.score.toFixed(1)}</span>
                                    <Badge
                                      className={
                                        item.data.verdict === "GO"
                                          ? "bg-emerald-500/10 text-emerald-500"
                                          : item.data.verdict === "CONDITIONAL"
                                          ? "bg-amber-500/10 text-amber-500"
                                          : "bg-red-500/10 text-red-500"
                                      }
                                    >
                                      {item.data.verdict}
                                    </Badge>
                                  </>
                                )}
                                <span className="text-xs text-muted-foreground">
                                  {item.date.toLocaleDateString()}
                                </span>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div variants={fadeUp} initial="hidden" animate="visible" className="lg:col-span-1">
                  <Card className="border-border/50 bg-card/50 backdrop-blur-sm h-full">
                    <CardHeader>
                      <div className="flex items-center justify-between gap-3">
                        <CardTitle className="text-lg">Verdict Breakdown</CardTitle>
                        <Badge variant="outline" className="border-emerald-500/20 bg-emerald-500/10 text-emerald-200">
                          {totalVerdicts} total
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="relative">
                      {verdictData.every((d) => d.value === 0) ? (
                        <div className="flex h-[220px] items-center justify-center text-muted-foreground">No data yet</div>
                      ) : (
                        <DashboardCharts
                          scoreDistribution={scoreDistribution}
                          verdictBreakdown={verdictBreakdown}
                          scoreTrend={scoreTrend}
                          agentPerformance={agentPerformance}
                          singleChart="verdict"
                          active={activeTab === "overview"}
                        />
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </div>
            </TabsContent>

            <TabsContent value="live" className="outline-none">
              {activeTab === "live" && (
                <motion.div variants={fadeUp} initial="hidden" animate="visible">
                  <LiveMonitor
                    activePipelines={activePipelines}
                    events={events}
                    nodeStatuses={nodeStatuses}
                    connected={connected}
                  />
                </motion.div>
              )}
            </TabsContent>

            <TabsContent value="deployed" className="outline-none">
              {activeTab === "deployed" && (
                <motion.div variants={fadeUp} initial="hidden" animate="visible">
                  <DeployedApps deployments={deployments} />
                </motion.div>
              )}
            </TabsContent>

            <TabsContent value="history" className="outline-none">
              {activeTab === "history" && (
                <motion.div variants={fadeUp} initial="hidden" animate="visible">
                  <HistoryList results={results} brainstorms={brainstorms} />
                </motion.div>
              )}
            </TabsContent>

            <TabsContent value="analytics" className="outline-none">
              {activeTab === "analytics" && (
                <motion.div variants={fadeUp} initial="hidden" animate="visible">
                  <DashboardCharts
                    scoreDistribution={scoreDistribution}
                    verdictBreakdown={verdictBreakdown}
                    scoreTrend={scoreTrend}
                    agentPerformance={agentPerformance}
                    active={activeTab === "analytics"}
                  />
                </motion.div>
              )}
            </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
