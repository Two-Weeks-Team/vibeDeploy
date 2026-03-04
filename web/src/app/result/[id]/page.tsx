"use client";

import { useParams } from "next/navigation";

/**
 * Result Dashboard — shows Vibe Score, individual analyses, debate transcript,
 * generated docs/code, and deployment status.
 * TODO (Wave 6): Fetch result from API, render score visualization,
 * tabbed content (analyses, debate, docs, code, deploy).
 */
export default function ResultPage() {
  const params = useParams<{ id: string }>();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="w-full max-w-5xl space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold">Results</h1>
          <p className="text-muted-foreground">
            Vibe Council verdict for session {params.id}
          </p>
        </div>

        {/* TODO: Vibe Score visualization */}
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          Result dashboard — coming in Wave 6
        </div>
      </div>
    </div>
  );
}
