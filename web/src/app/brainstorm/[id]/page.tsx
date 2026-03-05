"use client";

import { useParams } from "next/navigation";
import { BrainstormView } from "@/components/brainstorm-view";

export default function BrainstormPage() {
  const params = useParams<{ id: string }>();

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(168,85,247,0.16),transparent_42%),radial-gradient(circle_at_bottom_right,rgba(245,158,11,0.16),transparent_42%)] px-4 py-8 md:px-6">
      <div className="mx-auto w-full max-w-[1680px] space-y-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
            Brainstorm Session
          </h1>
          <p className="text-sm text-muted-foreground md:text-base">
            The Vibe Council is brainstorming creative ideas.
          </p>
          <p className="text-xs text-muted-foreground/80">
            Session: {params.id}
          </p>
        </div>
        <BrainstormView sessionId={params.id} />
      </div>
    </div>
  );
}
