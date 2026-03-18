"use client";

import { useState } from "react";
import type { ZPCard, CardStatus } from "@/types/zero-prompt";
import { KanbanColumn } from "./kanban-column";
import { CardDetailModal } from "./card-detail-modal";

interface KanbanBoardProps {
  cards: ZPCard[];
  onQueueBuild: (cardId: string) => void;
  onPassCard: (cardId: string) => void;
  onDeleteCard?: (cardId: string) => void;
}

const COLUMNS: { id: string; title: string; statuses: CardStatus[] }[] = [
  { id: "analyzing", title: "Exploring", statuses: ["analyzing"] },
  { id: "go_ready", title: "GO Ready", statuses: ["go_ready"] },
  { id: "building", title: "Building", statuses: ["build_queued", "building"] },
  { id: "deployed", title: "Deployed", statuses: ["deployed"] },
  { id: "nogo", title: "NO-GO / Passed", statuses: ["nogo", "passed", "build_failed"] },
];

export function KanbanBoard({ cards, onQueueBuild, onPassCard, onDeleteCard }: KanbanBoardProps) {
  const [selectedCard, setSelectedCard] = useState<ZPCard | null>(null);

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6 overflow-x-auto pb-4">
        {COLUMNS.map((col) => (
          <KanbanColumn
            key={col.id}
            id={col.id}
            title={col.title}
            statuses={col.statuses}
            cards={cards}
            onQueueBuild={onQueueBuild}
            onPassCard={onPassCard}
            onDeleteCard={onDeleteCard}
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
      />
    </>
  );
}
