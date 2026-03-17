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

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardContent className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-400" /> 탐색 중
            </p>
            <p className="text-2xl font-bold mt-1">{analyzedCount}</p>
          </div>
          <Badge variant="outline" className={isConnected ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" : "bg-red-500/10 text-red-500 border-red-500/20"}>
            {isConnected ? "Live" : "Offline"}
          </Badge>
        </CardContent>
      </Card>
      
      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardContent className="p-4">
          <p className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <PlayCircle className="w-4 h-4 text-amber-400" /> GO 대기
          </p>
          <p className="text-2xl font-bold mt-1">{goReadyCount}</p>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardContent className="p-4">
          <p className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <Clock className="w-4 h-4 text-purple-400" /> 빌드 중
          </p>
          <p className="text-2xl font-bold mt-1">{buildQueueCount}</p>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
        <CardContent className="p-4">
          <p className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" /> 배포됨
          </p>
          <p className="text-2xl font-bold mt-1">{deployedCount}</p>
        </CardContent>
      </Card>
    </div>
  );
}
