"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ZPAction } from "@/types/zero-prompt";

interface ActionFeedProps {
  actions: ZPAction[];
}

export function ActionFeed({ actions }: ActionFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [actions.length, autoScroll]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 10;
    setAutoScroll(isAtBottom);
  };

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm h-64 flex flex-col">
      <CardHeader className="py-3 px-4 border-b border-border/50">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Terminal className="w-4 h-4" /> Action Feed
          {!autoScroll && (
            <button 
              type="button"
              className="text-xs text-muted-foreground ml-auto cursor-pointer hover:text-foreground bg-transparent border-none p-0" 
              onClick={() => setAutoScroll(true)}
            >
              Resume auto-scroll
            </button>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent 
        className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-2"
        ref={scrollRef}
        onScroll={handleScroll}
      >
        {actions.length === 0 ? (
          <div className="text-muted-foreground text-center py-8">No actions yet...</div>
        ) : (
          actions.slice().reverse().map((action) => (
            <div key={`${action.timestamp}-${action.type}-${action.message.substring(0, 20)}`} className="flex gap-3">
              <span className="text-muted-foreground shrink-0">
                {new Date(action.timestamp).toLocaleTimeString()}
              </span>
              <span className="text-blue-400 shrink-0">[{action.type}]</span>
              <span className="text-foreground break-all">{action.message}</span>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
