"use client";

import { useState, useEffect } from "react";
import type { ZPCard, CardStatus } from "@/types/zero-prompt";
import { KanbanColumn } from "./kanban-column";
import { CardDetailModal } from "./card-detail-modal";

interface KanbanBoardProps {
  cards: ZPCard[];
  deployedCards?: ZPCard[];
  sessionId?: string;
  onQueueBuild: (cardId: string) => void;
  onPassCard: (cardId: string) => void;
  onDeleteCard?: (cardId: string) => void;
  onDeleteRejectedCards?: () => void;
  onReExplore?: (cardId: string) => void;
  autoCloseMs?: number;
  selectedCardId?: string | null;
  onSelectedCardChange?: (cardId: string | null) => void;
}

const COLUMN_LIMITS: Partial<Record<string, number>> = {
  analyzing: 5,
  go_ready: 5,
  nogo: 5,
};

const COLUMNS: { id: string; title: string; statuses: CardStatus[] }[] = [
  { id: "analyzing", title: "Exploring", statuses: ["analyzing"] },
  { id: "go_ready", title: "GO Ready", statuses: ["go_ready"] },
  { id: "building", title: "Building", statuses: ["build_queued", "building"] },
  { id: "deployed", title: "Live", statuses: ["deployed"] },
  { id: "nogo", title: "Rejected / Skipped", statuses: ["nogo", "passed", "build_failed"] },
];

export function KanbanBoard({ cards, deployedCards = [], sessionId, onQueueBuild, onPassCard, onDeleteCard, onDeleteRejectedCards, onReExplore, autoCloseMs, selectedCardId, onSelectedCardChange }: KanbanBoardProps) {
  const [internalSelectedCard, setInternalSelectedCard] = useState<ZPCard | null>(null);
  const liveCards = [
    ...cards.filter((card) => card.status === "deployed"),
    ...deployedCards.filter((card) => !cards.some((sessionCard) => sessionCard.card_id === card.card_id)),
  ];
  const cardsForBoard = [
    ...cards.filter((card) => card.status !== "deployed"),
    ...liveCards,
  ];
  const selectedCard = onSelectedCardChange
    ? cardsForBoard.find((card) => card.card_id === selectedCardId) ?? null
    : internalSelectedCard;

  const setSelectedCard = (card: ZPCard | null) => {
    if (onSelectedCardChange) {
      onSelectedCardChange(card?.card_id ?? null);
      return;
    }
    setInternalSelectedCard(card);
  };

  useEffect(() => {
    if (!selectedCard || !autoCloseMs) return;
    const timer = setTimeout(() => {
      if (onSelectedCardChange) {
        onSelectedCardChange(null);
      } else {
        setInternalSelectedCard(null);
      }
    }, autoCloseMs);
    return () => clearTimeout(timer);
  }, [selectedCard, autoCloseMs, onSelectedCardChange]);

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6 overflow-x-auto pb-4">
        {COLUMNS.map((col) => (
          <KanbanColumn
            key={col.id}
            id={col.id}
            title={col.title}
            statuses={col.statuses}
            cards={cardsForBoard}
            maxItems={COLUMN_LIMITS[col.id]}
            sessionId={sessionId}
            onDeleteRejectedCards={col.id === "nogo" ? onDeleteRejectedCards : undefined}
            onQueueBuild={onQueueBuild}
            onPassCard={onPassCard}
            onDeleteCard={onDeleteCard}
            onReExplore={onReExplore}
            onCardClick={setSelectedCard}
          />
        ))}
      </div>

      <CardDetailModal
        card={selectedCard}
        isOpen={!!selectedCard}
        onClose={() => setSelectedCard(null)}
        onQueueBuild={onQueueBuild}
        onPassCard={onPassCard}
        onDeleteCard={onDeleteCard}
      />
    </>
  );
}
