"use client";

import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
  CartesianGrid,
} from "recharts";
import type { ScoreDistributionBin, AgentPerformance, VerdictType } from "@/types/dashboard";

interface DashboardChartsProps {
  scoreDistribution: ScoreDistributionBin[];
  verdictBreakdown: Record<VerdictType, number>;
  scoreTrend: Array<{ date: string; score: number }>;
  agentPerformance: AgentPerformance[];
  singleChart?: "verdict" | "score" | "trend" | "agent";
  active?: boolean;
}

interface ChartSize {
  width: number;
  height: number;
}

interface ChartSurfaceProps {
  active: boolean;
  className?: string;
  children: (size: ChartSize) => ReactNode;
}

const VERDICT_COLORS = {
  GO: "#10b981",
  CONDITIONAL: "#f59e0b",
  "NO-GO": "#ef4444",
};

function ChartSurface({ active, className, children }: ChartSurfaceProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState<ChartSize>({ width: 0, height: 0 });

  useEffect(() => {
    if (!active) return;
    const element = ref.current;
    if (!element) return;

    const update = () => {
      const nextWidth = Math.floor(element.clientWidth);
      const nextHeight = Math.floor(element.clientHeight);
      setSize((prev) =>
        prev.width === nextWidth && prev.height === nextHeight
          ? prev
          : { width: nextWidth, height: nextHeight },
      );
    };

    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, [active]);

  return (
    <div ref={ref} className={className}>
      {active && size.width > 0 && size.height > 0 ? children(size) : null}
    </div>
  );
}

export function DashboardCharts({
  scoreDistribution,
  verdictBreakdown,
  scoreTrend,
  agentPerformance,
  singleChart,
  active = true,
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
      <div className="relative h-[220px] w-full">
        {!hasVerdictData ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">No data yet</div>
        ) : (
          <>
            <ChartSurface active={active} className="h-full w-full">
              {({ width, height }) => (
                <PieChart width={width} height={height}>
                  <Pie
                    data={verdictData}
                    cx={width / 2}
                    cy={height / 2}
                    innerRadius={Math.min(width, height) * 0.25}
                    outerRadius={Math.min(width, height) * 0.38}
                    paddingAngle={2}
                    dataKey="value"
                    stroke="none"
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))" }}
                    itemStyle={{ color: "hsl(var(--foreground))" }}
                  />
                </PieChart>
              )}
            </ChartSurface>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-bold">{totalVerdicts}</span>
              <span className="text-xs text-muted-foreground">Total verdicts</span>
            </div>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Score Distribution</CardTitle>
            <Badge variant="outline" className="border-blue-500/20 bg-blue-500/10 text-blue-300">
              {scoreDistribution.reduce((sum, bin) => sum + bin.count, 0)} runs
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="min-w-0 h-[320px]">
          {!hasScoreData ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">No data yet</div>
          ) : (
            <ChartSurface active={active} className="h-full w-full min-w-0">
              {({ width, height }) => (
                <BarChart width={width} height={height} data={scoreDistribution} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="range" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    cursor={{ fill: "hsl(var(--muted)/0.5)" }}
                    contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))" }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                </BarChart>
              )}
            </ChartSurface>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Verdict Breakdown</CardTitle>
            <Badge variant="outline" className="border-emerald-500/20 bg-emerald-500/10 text-emerald-300">
              {totalVerdicts} total
            </Badge>
          </div>
          <div className="flex flex-wrap gap-2">
            {verdictData.map((entry) => (
              <Badge
                key={entry.name}
                variant="outline"
                className="border-border/40 bg-background/30 text-foreground"
              >
                <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: entry.fill }} />
                {entry.name}: {entry.value}
              </Badge>
            ))}
          </div>
        </CardHeader>
        <CardContent className="relative min-w-0 h-[320px]">
          {!hasVerdictData ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">No data yet</div>
          ) : (
            <>
              <ChartSurface active={active} className="h-full w-full min-w-0">
                {({ width, height }) => (
                  <PieChart width={width} height={height}>
                    <Pie
                      data={verdictData}
                      cx={width / 2}
                      cy={height / 2}
                      innerRadius={Math.min(width, height) * 0.26}
                      outerRadius={Math.min(width, height) * 0.38}
                      paddingAngle={2}
                      dataKey="value"
                      stroke="none"
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))" }}
                      itemStyle={{ color: "hsl(var(--foreground))" }}
                    />
                  </PieChart>
                )}
              </ChartSurface>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold">{totalVerdicts}</span>
                <span className="text-xs text-muted-foreground">Total</span>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Score Trend</CardTitle>
            <Badge variant="outline" className="border-cyan-500/20 bg-cyan-500/10 text-cyan-300">
              {scoreTrend.length} points
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="min-w-0 h-[320px]">
          {!hasTrendData ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">No data yet</div>
          ) : (
            <ChartSurface active={active} className="h-full w-full min-w-0">
              {({ width, height }) => (
                <AreaChart width={width} height={height} data={scoreTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.35} />
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
              )}
            </ChartSurface>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardHeader className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Agent Performance</CardTitle>
            <Badge variant="outline" className="border-violet-500/20 bg-violet-500/10 text-violet-300">
              {agentPerformance.length} agents
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="min-w-0 h-[320px]">
          {!hasAgentData ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">No data yet</div>
          ) : (
            <ChartSurface active={active} className="h-full w-full min-w-0">
              {({ width, height }) => (
                <RadarChart width={width} height={height} cx={width / 2} cy={height / 2} outerRadius={Math.min(width, height) * 0.3} data={agentPerformance}>
                  <PolarGrid stroke="hsl(var(--border))" />
                  <PolarAngleAxis dataKey="agent" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                  <Radar name="Avg Score" dataKey="avgScore" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.28} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))" }}
                  />
                </RadarChart>
              )}
            </ChartSurface>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
