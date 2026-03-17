"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal, Search } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import type { ZPAction } from "@/types/zero-prompt";

interface ActionFeedProps {
  actions: ZPAction[];
}

export function ActionFeed({ actions }: ActionFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState<string | null>(null);

  const filteredActions = actions.filter(action => {
    const matchesText = action.message.toLowerCase().includes(filter.toLowerCase()) || 
                        action.type.toLowerCase().includes(filter.toLowerCase());
    const matchesType = typeFilter ? action.type === typeFilter : true;
    return matchesText && matchesType;
  });

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filteredActions.length, autoScroll]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 10;
    setAutoScroll(isAtBottom);
  };

  const uniqueTypes = Array.from(new Set(actions.map(a => a.type)));

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur-sm h-96 flex flex-col">
      <CardHeader className="py-3 px-4 border-b border-border/50 space-y-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Terminal className="w-4 h-4" /> Action Feed
            <Badge variant="secondary" className="text-[10px] ml-2">
              {filteredActions.length} events
            </Badge>
          </CardTitle>
          {!autoScroll && (
            <button 
              type="button"
              className="text-xs text-muted-foreground cursor-pointer hover:text-foreground bg-transparent border-none p-0" 
              onClick={() => setAutoScroll(true)}
            >
              Resume auto-scroll
            </button>
          )}
        </div>
        
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
            <Input 
              placeholder="Filter logs..." 
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="h-7 text-xs pl-7 bg-background/50"
            />
          </div>
          <div className="flex gap-1 overflow-x-auto pb-1 sm:pb-0 hide-scrollbar">
            <Badge 
              variant={typeFilter === null ? "default" : "outline"}
              className="cursor-pointer text-[10px] whitespace-nowrap"
              onClick={() => setTypeFilter(null)}
            >
              All
            </Badge>
            {uniqueTypes.map(type => (
              <Badge 
                key={type}
                variant={typeFilter === type ? "default" : "outline"}
                className="cursor-pointer text-[10px] whitespace-nowrap"
                onClick={() => setTypeFilter(type === typeFilter ? null : type)}
              >
                {type}
              </Badge>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent 
        className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-2"
        ref={scrollRef}
        onScroll={handleScroll}
      >
        {filteredActions.length === 0 ? (
          <div className="text-muted-foreground text-center py-8">
            {actions.length === 0 ? "No actions yet..." : "No actions match your filter."}
          </div>
        ) : (
          filteredActions.slice().reverse().map((action) => (
            <div key={`${action.timestamp}-${action.type}-${action.message.substring(0, 20)}`} className="flex gap-3 hover:bg-muted/30 p-1 rounded transition-colors">
              <span className="text-muted-foreground shrink-0">
                {new Date(action.timestamp).toLocaleTimeString()}
              </span>
              <span className="text-blue-400 shrink-0 w-20 truncate" title={action.type}>
                [{action.type}]
              </span>
              <span className="text-foreground break-all">{action.message}</span>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
