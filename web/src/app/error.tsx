"use client";

import { useEffect, useRef } from "react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const retriedRef = useRef(false);

  useEffect(() => {
    const message = String(error?.message || "");
    const isChunkError = message.includes("ChunkLoadError") || message.includes("Failed to load chunk");
    if (!retriedRef.current && isChunkError) {
      retriedRef.current = true;
      window.location.reload();
    }
  }, [error]);

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-6">
      <div className="max-w-md w-full rounded-xl border border-border/50 bg-card p-6 space-y-4 shadow-sm">
        <h2 className="text-2xl font-semibold text-destructive">Something went wrong</h2>
        <p className="text-sm text-muted-foreground break-words">{String(error?.message || "Unknown error")}</p>
        <button
          type="button"
          onClick={reset}
          className="w-full rounded-md bg-foreground text-background py-2.5 text-sm font-medium"
        >
          Reload
        </button>
      </div>
    </div>
  );
}
