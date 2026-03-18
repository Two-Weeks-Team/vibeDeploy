"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import { cn } from "@/lib/utils";

interface VibeScoreProps {
  score: number;
  breakdown?: {
    tech: number;
    market: number;
    innovation: number;
    risk: number;
    userImpact: number;
  };
}

export function VibeScore({ score, breakdown }: VibeScoreProps) {
  const [displayScore, setDisplayScore] = useState(0);

  useEffect(() => {
    const clamped = Math.max(0, Math.min(100, Math.round(score)));
    const start = performance.now();
    const duration = 900;

    const frame = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      setDisplayScore(Math.round(clamped * progress));
      if (progress < 1) {
        requestAnimationFrame(frame);
      }
    };

    const raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [score]);

  const verdict = score >= 75 ? "GO" : score >= 50 ? "CONDITIONAL" : "NO-GO";

  const color =
    verdict === "GO"
      ? "bg-emerald-500/15 text-emerald-300"
      : verdict === "CONDITIONAL"
        ? "bg-amber-500/20 text-amber-200"
        : "bg-red-500/15 text-red-300";

  const chartData = useMemo(() => {
    if (!breakdown) return [];

    return [
      { axis: "Tech", value: breakdown.tech },
      { axis: "Market", value: breakdown.market },
      { axis: "Innovation", value: breakdown.innovation },
      { axis: "Risk Safety", value: 100 - breakdown.risk },
      { axis: "UX", value: breakdown.userImpact },
    ];
  }, [breakdown]);

  return (
    <Card className="border-white/10 bg-card/60">
      <CardContent className="grid gap-5 p-5 lg:grid-cols-[1fr_1.4fr] lg:items-center">
        <div className="flex flex-col items-center justify-center gap-2 text-center">
          <motion.div
            key={score}
            initial={{ scale: 0.92, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.32 }}
            className="text-5xl font-bold tracking-tight"
          >
            {displayScore}
          </motion.div>
          <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Vibe Score</p>
          <Badge className={cn("px-3 py-1 text-xs", color)}>{verdict}</Badge>
        </div>

        {breakdown && (
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={chartData} outerRadius="72%">
                <PolarGrid stroke="rgba(255,255,255,0.15)" />
                <PolarAngleAxis dataKey="axis" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Radar
                  dataKey="value"
                  stroke="#22c55e"
                  fill="#22c55e"
                  fillOpacity={0.32}
                  animationDuration={700}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        )}

        {breakdown && (
          <div className="grid grid-cols-2 gap-2 text-xs lg:col-span-2">
            <Metric label="Tech" value={breakdown.tech} />
            <Metric label="Market" value={breakdown.market} />
            <Metric label="Innovation" value={breakdown.innovation} />
            <Metric label="Risk" value={breakdown.risk} inverted />
            <Metric label="User Impact" value={breakdown.userImpact} className="col-span-2" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({
  label,
  value,
  inverted = false,
  className,
}: {
  label: string;
  value: number;
  inverted?: boolean;
  className?: string;
}) {
  const shown = Math.max(0, Math.min(100, Math.round(inverted ? 100 - value : value)));

  return (
    <div className={cn("rounded-lg border border-white/10 bg-muted/20 px-3 py-2", className)}>
      <div className="mb-1 flex items-center justify-between text-muted-foreground">
        <span>{label}</span>
        <span>{shown}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full rounded-full bg-primary"
          initial={{ width: 0 }}
          animate={{ width: `${shown}%` }}
          transition={{ duration: 0.7 }}
        />
      </div>
    </div>
  );
}
