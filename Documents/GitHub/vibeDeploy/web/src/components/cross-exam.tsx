"use client";

/**
 * CrossExam — Displays the cross-examination debate between council members.
 * Shows structured debate pairs: Architect↔Guardian, Scout↔Catalyst, etc.
 * TODO (Wave 5): Real-time debate rendering, argument/counter-argument cards.
 */

interface DebateExchange {
  from: string;
  to: string;
  argument: string;
  response?: string;
}

interface CrossExamProps {
  exchanges: DebateExchange[];
}

export function CrossExam({ exchanges }: CrossExamProps) {
  return (
    <div className="space-y-4">
      <h3 className="font-semibold">Cross-Examination</h3>
      {exchanges.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Debate has not started yet.
        </p>
      ) : (
        exchanges.map((ex) => (
          <div key={`${ex.from}-${ex.to}-${ex.argument.slice(0, 20)}`} className="rounded-lg border p-3 text-sm">
            <p className="font-medium">
              {ex.from} → {ex.to}
            </p>
            <p className="text-muted-foreground">{ex.argument}</p>
            {ex.response && (
              <p className="mt-1 border-t pt-1 text-muted-foreground">
                ↳ {ex.response}
              </p>
            )}
          </div>
        ))
      )}
    </div>
  );
}
