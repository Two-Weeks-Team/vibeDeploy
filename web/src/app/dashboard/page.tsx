"use client";

import { useMemo } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Activity, Target, Brain, CheckCircle, XCircle, Zap, TrendingUp } from "lucide-react";
import { useDashboard } from "@/hooks/use-dashboard";
import { usePipelineMonitor } from "@/hooks/use-pipeline-monitor";
import { PipelineViz } from "@/components/dashboard/pipeline-viz";
import { DashboardCharts } from "@/components/dashboard/dashboard-charts";
import { HistoryList } from "@/components/dashboard/history-list";
import { LiveMonitor } from "@/components/dashboard/live-monitor";
import { PieChart, Pie, ResponsiveContainer, Tooltip } from "recharts";
import type { VerdictType } from "@/types/dashboard";

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
  const {
    healthy,
    stats,
    results,
    brainstorms,
    loading,
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
        </header>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-2 lg:grid-cols-4 mb-8">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="live">
              Live Monitor
              {activePipelines.length > 0 && (
                <span className="ml-2 flex h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
              )}
            </TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
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
                <h2 className="text-lg font-semibold mb-4">Architecture Overview</h2>
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
                            <div key={item.type === "evaluation" ? item.data.thread_id : item.data.thread_id} className="flex items-center justify-between p-3 rounded-lg bg-accent/50">
                              <div className="flex items-center gap-3">
                                {item.type === "evaluation" ? (
                                  <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">Eval</Badge>
                                ) : (
                                  <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/20">Brainstorm</Badge>
                                )}
                                <span className="font-mono text-sm text-muted-foreground">
                                  {item.data.thread_id.substring(0, 8)}
                                </span>
                              </div>
                              <div className="flex items-center gap-4">
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
                      <CardTitle className="text-lg">Verdict Breakdown</CardTitle>
                    </CardHeader>
                    <CardContent className="h-[300px] relative">
                      {verdictData.every((d) => d.value === 0) ? (
                        <div className="h-full flex items-center justify-center text-muted-foreground">No data yet</div>
                      ) : (
                        <>
                          <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                              <Pie
                                data={verdictData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={90}
                                paddingAngle={2}
                                dataKey="value"
                                stroke="none"
                              />
                              <Tooltip
                                contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))" }}
                                itemStyle={{ color: "hsl(var(--foreground))" }}
                              />
                            </PieChart>
                          </ResponsiveContainer>
                          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                            <span className="text-2xl font-bold">{stats.total_meetings}</span>
                            <span className="text-xs text-muted-foreground">Total</span>
                          </div>
                        </>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              </div>
            </TabsContent>

            <TabsContent value="live" className="outline-none">
              <motion.div variants={fadeUp} initial="hidden" animate="visible">
                <LiveMonitor
                  activePipelines={activePipelines}
                  events={events}
                  nodeStatuses={nodeStatuses}
                  connected={connected}
                />
              </motion.div>
            </TabsContent>

            <TabsContent value="history" className="outline-none">
              <motion.div variants={fadeUp} initial="hidden" animate="visible">
                <HistoryList results={results} brainstorms={brainstorms} />
              </motion.div>
            </TabsContent>

            <TabsContent value="analytics" className="outline-none">
              <motion.div variants={fadeUp} initial="hidden" animate="visible">
                <DashboardCharts
                  scoreDistribution={scoreDistribution}
                  verdictBreakdown={verdictBreakdown}
                  scoreTrend={scoreTrend}
                  agentPerformance={agentPerformance}
                />
              </motion.div>
            </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
