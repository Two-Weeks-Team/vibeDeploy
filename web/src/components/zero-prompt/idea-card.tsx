"use client";

import { motion } from "framer-motion";
import { Play, X, ExternalLink, Loader2, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ZPCard } from "@/types/zero-prompt";

interface IdeaCardProps {
  card: ZPCard;
  onQueueBuild: (cardId: string) => void;
  onPassCard: (cardId: string) => void;
  onDeleteCard?: (cardId: string) => void;
  onClick?: (card: ZPCard) => void;
}

export function IdeaCard({ card, onQueueBuild, onPassCard, onDeleteCard, onClick }: IdeaCardProps) {
  return (
    <motion.div
      layoutId={card.card_id}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-card border border-border/50 rounded-lg shadow-sm overflow-hidden cursor-pointer hover:border-primary/50 transition-colors"
      onClick={() => onClick?.(card)}
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
          <div className="flex gap-2 mt-3" onClick={(e) => e.stopPropagation()}>
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

        {(card.status === "nogo" || card.status === "passed" || card.status === "build_failed") && onDeleteCard && (
          <div className="flex gap-2 mt-3" onClick={(e) => e.stopPropagation()}>
            <Button 
              size="sm" 
              variant="ghost" 
              className="flex-1 h-8 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={() => onDeleteCard(card.card_id)}
            >
              <Trash2 className="w-3 h-3 mr-1" /> 삭제
            </Button>
          </div>
        )}

        {card.status === "deployed" && (
          <Button 
            size="sm" 
            variant="outline" 
            className="w-full mt-3 h-8 text-xs border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10"
            asChild
            onClick={(e) => e.stopPropagation()}
          >
            <a href={`https://${card.card_id}.ondigitalocean.app`} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="w-3 h-3 mr-1" /> View App
            </a>
          </Button>
        )}
      </div>
    </motion.div>
  );
}
