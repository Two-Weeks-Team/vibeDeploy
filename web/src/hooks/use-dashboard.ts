"use client";

import { useCallback, useEffect, useState } from "react";
import {
  checkHealth,
  getDashboardStats,
  getDashboardResults,
  getDashboardBrainstorms,
  getDashboardDeployments,
} from "@/lib/api";
import type {
  DashboardStats,
  MeetingResultFull,
  BrainstormResultFull,
  ScoreDistributionBin,
  AgentPerformance,
  VerdictType,
  DeployedApp,
} from "@/types/dashboard";

const POLL_MS = 5_000;

function computeScoreDistribution(results: MeetingResultFull[]): ScoreDistributionBin[] {
  const bins = [
    { range: "0–25", count: 0, color: "#ef4444" },
    { range: "26–50", count: 0, color: "#f59e0b" },
    { range: "51–75", count: 0, color: "#eab308" },
    { range: "76–100", count: 0, color: "#22c55e" },
  ];
  for (const r of results) {
    const s = r.score ?? 0;
    if (s <= 25) bins[0].count++;
    else if (s <= 50) bins[1].count++;
    else if (s <= 75) bins[2].count++;
    else bins[3].count++;
  }
  return bins;
}

function computeVerdictBreakdown(results: MeetingResultFull[]): Record<VerdictType, number> {
  const m: Record<VerdictType, number> = { GO: 0, CONDITIONAL: 0, "NO-GO": 0 };
  for (const r of results) {
    const v = r.verdict as VerdictType;
    if (v in m) m[v]++;
  }
  return m;
}

function computeAgentPerformance(results: MeetingResultFull[]): AgentPerformance[] {
  const acc: Record<string, { total: number; count: number }> = {};
  for (const r of results) {
    for (const a of r.analyses ?? []) {
      if (!a.agent || a.score == null) continue;
      if (!acc[a.agent]) acc[a.agent] = { total: 0, count: 0 };
      acc[a.agent].total += a.score;
      acc[a.agent].count++;
    }
  }
  return Object.entries(acc)
    .map(([agent, { total, count }]) => ({
      agent,
      avgScore: Math.round(total / count),
      count,
    }))
    .sort((a, b) => b.avgScore - a.avgScore);
}

function computeScoreTrend(results: MeetingResultFull[]): Array<{ date: string; score: number }> {
  return [...results]
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    .map((r) => ({
      date: new Date(r.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      score: r.score ?? 0,
    }));
}

export function useDashboard() {
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const [stats, setStats] = useState<DashboardStats>({
    total_meetings: 0,
    total_brainstorms: 0,
    avg_score: 0,
    go_count: 0,
    nogo_count: 0,
  });
  const [results, setResults] = useState<MeetingResultFull[]>([]);
  const [brainstorms, setBrainstorms] = useState<BrainstormResultFull[]>([]);
  const [deployments, setDeployments] = useState<DeployedApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const health = await checkHealth();
      setHealthy(health);

      if (!health) {
        setLoading(false);
        return;
      }

      const [s, r, b, d] = await Promise.all([
        getDashboardStats(),
        getDashboardResults(),
        getDashboardBrainstorms(),
        getDashboardDeployments(),
      ]);
      setStats(s);
      setResults(r as unknown as MeetingResultFull[]);
      setBrainstorms(b as unknown as BrainstormResultFull[]);
      setDeployments(d);
      setLastUpdated(Date.now());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(refresh, 0);
    const id = setInterval(refresh, POLL_MS);
    return () => {
      clearTimeout(t);
      clearInterval(id);
    };
  }, [refresh]);

  return {
    healthy,
    stats,
    results,
    brainstorms,
    deployments,
    loading,
    lastUpdated,
    refresh,
    scoreDistribution: computeScoreDistribution(results),
    verdictBreakdown: computeVerdictBreakdown(results),
    agentPerformance: computeAgentPerformance(results),
    scoreTrend: computeScoreTrend(results),
  };
}
