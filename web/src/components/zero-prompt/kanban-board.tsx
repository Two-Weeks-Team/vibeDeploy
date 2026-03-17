"use client";

import { motion } from "framer-motion";
import { Play, X, ExternalLink, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ZPCard, CardStatus } from "@/types/zero-prompt";

interface KanbanBoardProps {
  cards: ZPCard[];
  onQueueBuild: (cardId: string) => void;
  onPassCard: (cardId: string) => void;
}

const COLUMNS: { id: string; title: string; statuses: CardStatus[] }[] = [
  { id: "analyzing", title: "탐색 중", statuses: ["analyzing"] },
  { id: "go_ready", title: "GO 대기", statuses: ["go_ready"] },
  { id: "building", title: "빌드 중", statuses: ["build_queued", "building"] },
  { id: "deployed", title: "배포됨", statuses: ["deployed"] },
  { id: "nogo", title: "NO-GO / 패스", statuses: ["nogo", "passed", "build_failed"] },
];

export function KanbanBoard({ cards, onQueueBuild, onPassCard }: KanbanBoardProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6 overflow-x-auto pb-4">
      {COLUMNS.map((col) => {
        const columnCards = cards.filter((c) => col.statuses.includes(c.status));
        
        return (
          <div key={col.id} className="flex flex-col min-w-[280px] bg-muted/30 rounded-xl p-3 border border-border/50">
            <div className="flex items-center justify-between mb-3 px-1">
              <h3 className="font-semibold text-sm">{col.title}</h3>
              <Badge variant="secondary" className="text-xs">{columnCards.length}</Badge>
            </div>
            
            <div className="flex flex-col gap-3 flex-1">
              {columnCards.length === 0 ? (
                <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground border-2 border-dashed border-border/50 rounded-lg p-4">
                  Empty
                </div>
              ) : (
                columnCards.map((card) => (
                  <motion.div
                    key={card.card_id}
                    layoutId={card.card_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-card border border-border/50 rounded-lg shadow-sm overflow-hidden"
                  >
                    <div className="p-3">
                      <div className="flex justify-between items-start mb-2">
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-5 bg-background">
                          {card.video_id}
                        </Badge>
                        {card.score > 0 && (
                          <span className={`text-xs font-bold ${card.score >= 70 ? 'text-emerald-500' : card.score >= 50 ? 'text-amber-500' : 'text-red-500'}`}>
                            {card.score.toFixed(1)}
                          </span>
                        )}
                      </div>
                      <h4 className="text-sm font-medium line-clamp-2 mb-2" title={card.title}>
                        {card.title}
                      </h4>
                      
                      {card.status === "go_ready" && (
                        <div className="flex gap-2 mt-3">
                          <Button 
                            size="sm" 
                            className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white h-8 text-xs"
                            onClick={() => onQueueBuild(card.card_id)}
                          >
                            <Play className="w-3 h-3 mr-1" /> GO!
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="flex-1 h-8 text-xs"
                            onClick={() => onPassCard(card.card_id)}
                          >
                            <X className="w-3 h-3 mr-1" /> 패스
                          </Button>
                        </div>
                      )}

                      {(card.status === "build_queued" || card.status === "building") && (
                        <div className="flex items-center justify-center gap-2 mt-3 text-xs text-muted-foreground bg-muted/50 py-1.5 rounded">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          {card.status === "build_queued" ? "Queued..." : "Building..."}
                        </div>
                      )}

                      {card.status === "deployed" && (
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="w-full mt-3 h-8 text-xs border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10"
                          asChild
                        >
                          <a href={`https://${card.card_id}.ondigitalocean.app`} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="w-3 h-3 mr-1" /> View App
                          </a>
                        </Button>
                      )}
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
