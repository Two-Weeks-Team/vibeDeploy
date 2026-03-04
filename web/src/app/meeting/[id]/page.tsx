"use client";

import { useParams } from "next/navigation";

/**
 * Live Meeting View — shows The Vibe Council debate in real-time via SSE.
 * TODO (Wave 5): Connect to SSE stream, render council member cards,
 * show phase transitions, display live scoring.
 */
export default function MeetingPage() {
  const params = useParams<{ id: string }>();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="w-full max-w-4xl space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold">The Vibe Council</h1>
          <p className="text-muted-foreground">
            Meeting in progress...
          </p>
          <p className="text-xs text-muted-foreground">
            Session: {params.id}
          </p>
        </div>

        {/* TODO: Council member cards with live speech bubbles */}
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          Live meeting view — coming in Wave 5
        </div>
      </div>
    </div>
  );
}
