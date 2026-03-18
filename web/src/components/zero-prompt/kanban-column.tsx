"use client";

import { Badge } from "@/components/ui/badge";
import type { ZPCard, CardStatus } from "@/types/zero-prompt";
import { IdeaCard } from "./idea-card";

interface KanbanColumnProps {
  id: string;
  title: string;
  statuses: CardStatus[];
  cards: ZPCard[];
  sessionId?: string;
  onQueueBuild: (cardId: string) => void;
  onPassCard: (cardId: string) => void;
  onDeleteCard?: (cardId: string) => void;
  onReExplore?: (cardId: string) => void;
  onCardClick?: (card: ZPCard) => void;
}

export function KanbanColumn({ title, statuses, cards, onQueueBuild, onPassCard, onDeleteCard, onReExplore, onCardClick }: KanbanColumnProps) {
  const columnCards = cards.filter((c) => statuses.includes(c.status));

  return (
    <div className="flex flex-col min-w-[280px] bg-muted/30 rounded-xl p-3 border border-border/50">
      <div className="flex items-center justify-between mb-3 px-1">
        <h3 className="font-semibold text-sm">{title}</h3>
        <Badge variant="secondary" className="text-xs">{columnCards.length}</Badge>
      </div>
      
      <div className="flex flex-col gap-3 flex-1 max-h-[688px] overflow-y-auto pr-1">
        {columnCards.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground border-2 border-dashed border-border/50 rounded-lg p-4">
              No ideas here yet
          </div>
        ) : (
          columnCards.map((card) => (
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
