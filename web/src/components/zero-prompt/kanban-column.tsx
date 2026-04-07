"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ZPCard, CardStatus } from "@/types/zero-prompt";
import { Trash2 } from "lucide-react";
import { IdeaCard } from "./idea-card";

interface KanbanColumnProps {
  id: string;
  title: string;
  statuses: CardStatus[];
  cards: ZPCard[];
  maxItems?: number;
  sessionId?: string;
  onDeleteRejectedCards?: () => void;
  onQueueBuild: (cardId: string) => void;
  onPassCard: (cardId: string) => void;
  onDeleteCard?: (cardId: string) => void;
  onReExplore?: (cardId: string) => void;
  onCardClick?: (card: ZPCard) => void;
}

export function KanbanColumn({ title, statuses, cards, maxItems, onDeleteRejectedCards, onQueueBuild, onPassCard, onDeleteCard, onReExplore, onCardClick }: KanbanColumnProps) {
  const columnCards = cards.filter((c) => statuses.includes(c.status));
  const visibleCards = maxItems ? columnCards.slice(-maxItems) : columnCards;
  const isWindowed = typeof maxItems === "number" && columnCards.length > maxItems;

  return (
    <div role="group" aria-label={`${title} column, ${columnCards.length} items`} className="flex flex-col min-w-[280px] bg-muted/30 rounded-xl p-3 border border-border/50">
      <div className="mb-3 space-y-2 px-1">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-semibold text-sm">{title}</h3>
          <Badge variant="secondary" className="text-xs">{columnCards.length}</Badge>
        </div>
        <div className="flex items-center justify-between gap-2">
          <p className="text-[11px] text-muted-foreground">
            {isWindowed ? `Showing latest ${visibleCards.length} of ${columnCards.length}` : `${columnCards.length} total`}
          </p>
          {onDeleteRejectedCards && columnCards.length > 0 ? (
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-[11px]"
              onClick={onDeleteRejectedCards}
            >
              <Trash2 className="mr-1 h-3 w-3" /> Clear all
            </Button>
          ) : null}
        </div>
      </div>
      
      <div className="flex flex-col gap-3 flex-1 max-h-[688px] overflow-y-auto pr-1">
        {visibleCards.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground border-2 border-dashed border-border/50 rounded-lg p-4">
              No ideas here yet
          </div>
        ) : (
          visibleCards.map((card) => (
            <IdeaCard
              key={card.card_id}
              card={card}
              onQueueBuild={onQueueBuild}
              onPassCard={onPassCard}
              onDeleteCard={onDeleteCard}
              onReExplore={onReExplore}
              onClick={onCardClick}
            />
          ))
        )}
      </div>
    </div>
  );
}
