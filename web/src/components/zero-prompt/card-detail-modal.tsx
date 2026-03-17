"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Play, X, ExternalLink } from "lucide-react";
import type { ZPCard } from "@/types/zero-prompt";

interface CardDetailModalProps {
  card: ZPCard | null;
  isOpen: boolean;
  onClose: () => void;
  onQueueBuild: (cardId: string) => void;
  onPassCard: (cardId: string) => void;
}

export function CardDetailModal({ card, isOpen, onClose, onQueueBuild, onPassCard }: CardDetailModalProps) {
  if (!card) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex justify-between items-start mb-2">
            <Badge variant="outline" className="bg-background">
              {card.video_id}
            </Badge>
            <Badge variant={card.status === "deployed" ? "default" : "secondary"}>
              {card.status.replace("_", " ").toUpperCase()}
            </Badge>
          </div>
          <DialogTitle className="text-xl">{card.title}</DialogTitle>
          <DialogDescription>
            Card ID: {card.card_id}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          <div>
            <h4 className="text-sm font-medium mb-1 text-muted-foreground">Vibe Score</h4>
            <div className="flex items-center gap-2">
              <span className={`text-2xl font-bold ${card.score >= 70 ? 'text-emerald-500' : card.score >= 50 ? 'text-amber-500' : 'text-red-500'}`}>
                {card.score.toFixed(1)}
              </span>
              <span className="text-sm text-muted-foreground">/ 100</span>
            </div>
          </div>

          {/* Placeholder for more details that could be added later */}
          <div className="bg-muted/30 p-4 rounded-lg border border-border/50">
            <p className="text-sm text-muted-foreground italic">
              Detailed analysis and council debate logs would appear here.
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-4">
          {card.status === "go_ready" && (
            <>
              <Button 
                variant="outline" 
                onClick={() => {
                  onPassCard(card.card_id);
                  onClose();
                }}
              >
                <X className="w-4 h-4 mr-2" /> Pass
              </Button>
              <Button 
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                onClick={() => {
                  onQueueBuild(card.card_id);
                  onClose();
                }}
              >
                <Play className="w-4 h-4 mr-2" /> GO! Build
              </Button>
            </>
          )}
          
          {card.status === "deployed" && (
            <Button asChild className="w-full sm:w-auto">
              <a href={`https://${card.card_id}.ondigitalocean.app`} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-4 h-4 mr-2" /> Open App
              </a>
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
