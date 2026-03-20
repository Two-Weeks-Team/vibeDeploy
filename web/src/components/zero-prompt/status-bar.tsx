"use client";

import { Activity, CheckCircle, Clock, PlayCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ZPSession } from "@/types/zero-prompt";

interface StatusBarProps {
  session: ZPSession | null;
  isConnected: boolean;
}

export function StatusBar({ session, isConnected }: StatusBarProps) {
  if (!session) return null;

  const cards = session.cards || [];
  const analyzedCount = cards.filter(c => c.status === "analyzing").length;
  const goReadyCount = cards.filter(c => c.status === "go_ready").length;
  const buildQueueCount = cards.filter(c => c.status === "build_queued" || c.status === "building").length;
  const deployedCount = cards.filter(c => c.status === "deployed").length;
  const sessionBadgeClass = session.status === "exploring"
    ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
    : session.status === "paused"
      ? "bg-amber-500/10 text-amber-500 border-amber-500/20"
      : "bg-blue-500/10 text-blue-500 border-blue-500/20";
  const sessionBadgeText = session.status === "exploring"
    ? (isConnected ? "Running" : "Reconnecting")
    : session.status === "paused"
      ? "Paused"
      : "Completed";

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardContent className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-400" /> Exploring
            </p>
            <p className="text-2xl font-bold mt-1">{analyzedCount}</p>
          </div>
          <Badge variant="outline" className={sessionBadgeClass}>
            {sessionBadgeText}
          </Badge>
        </CardContent>
      </Card>
      
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardContent className="p-4">
          <p className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <PlayCircle className="w-4 h-4 text-amber-400" /> GO Ready
          </p>
          <p className="text-2xl font-bold mt-1">{goReadyCount}</p>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardContent className="p-4">
          <p className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <Clock className="w-4 h-4 text-purple-400" /> Building
          </p>
          <p className="text-2xl font-bold mt-1">{buildQueueCount}</p>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardContent className="p-4">
          <p className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" /> Live
          </p>
          <p className="text-2xl font-bold mt-1">{deployedCount}</p>
        </CardContent>
      </Card>
    </div>
  );
}
