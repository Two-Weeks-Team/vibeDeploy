"use client";


import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  AreaChart,
  Area,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { ScoreDistributionBin, AgentPerformance, VerdictType } from "@/types/dashboard";

interface DashboardChartsProps {
  scoreDistribution: ScoreDistributionBin[];
  verdictBreakdown: Record<VerdictType, number>;
  scoreTrend: Array<{ date: string; score: number }>;
  agentPerformance: AgentPerformance[];
  singleChart?: "verdict" | "score" | "trend" | "agent";
}

const VERDICT_COLORS = {
  GO: "#10b981",
  CONDITIONAL: "#f59e0b",
  "NO-GO": "#ef4444",
};

export function DashboardCharts({
  scoreDistribution,
  verdictBreakdown,
  scoreTrend,
  agentPerformance,
  singleChart,
}: DashboardChartsProps) {
  const hasScoreData = scoreDistribution.some((b) => b.count > 0);
  const hasVerdictData = Object.values(verdictBreakdown).some((v) => v > 0);
  const hasTrendData = scoreTrend.length > 0;
  const hasAgentData = agentPerformance.length > 0;

  const verdictData = Object.entries(verdictBreakdown).map(([name, value]) => ({
    name,
    value,
    fill: VERDICT_COLORS[name as VerdictType],
  }));

  const totalVerdicts = verdictData.reduce((acc, curr) => acc + curr.value, 0);

  if (singleChart === "verdict") {
    return (
      <div className="w-full h-[200px] relative">
        {!hasVerdictData ? (
          <div className="h-full flex items-center justify-center text-muted-foreground">No data yet</div>
        ) : (
          <>
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                <Pie data={verdictData} cx="50%" cy="50%" innerRadius={60} outerRadius={85} paddingAngle={2} dataKey="value" stroke="none" />
                <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))" }} itemStyle={{ color: "hsl(var(--foreground))" }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-bold">{totalVerdicts}</span>
              <span className="text-[10px] text-muted-foreground">Total</span>
            </div>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Score Distribution</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px]">
          {!hasScoreData ? (
            <div className="h-full flex items-center justify-center text-muted-foreground">No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scoreDistribution} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="range" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip
                  cursor={{ fill: "hsl(var(--muted)/0.5)" }}
                  contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))" }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Verdict Breakdown</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] relative">
          {!hasVerdictData ? (
            <div className="h-full flex items-center justify-center text-muted-foreground">No data yet</div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={verdictData}
                    cx="50%"
                    cy="50%"
                    innerRadius={80}
                    outerRadius={110}
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
                <span className="text-3xl font-bold">{totalVerdicts}</span>
                <span className="text-xs text-muted-foreground">Total</span>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Score Trend</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px]">
          {!hasTrendData ? (
            <div className="h-full flex items-center justify-center text-muted-foreground">No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={scoreTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))" }}
                />
                <Area type="monotone" dataKey="score" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorScore)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Agent Performance</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px]">
          {!hasAgentData ? (
            <div className="h-full flex items-center justify-center text-muted-foreground">No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={agentPerformance}>
                <PolarGrid stroke="hsl(var(--border))" />
                <PolarAngleAxis dataKey="agent" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                <Radar name="Avg Score" dataKey="avgScore" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
                <Tooltip
                  contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))" }}
                />
              </RadarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
