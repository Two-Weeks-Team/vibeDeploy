import { Suspense } from "react";
import { DASHBOARD_API_URL } from "@/lib/api";
import { ZeroPromptWorkspace } from "@/components/zero-prompt/zero-prompt-workspace";
import type { ZPSession } from "@/types/zero-prompt";

async function getInitialSession(): Promise<ZPSession | null> {
  try {
    const response = await fetch(`${DASHBOARD_API_URL}/zero-prompt/dashboard`, { cache: "no-store" });
    if (!response.ok) return null;
    const data = await response.json();
    if (!data?.session_id) return null;
    return data as ZPSession;
  } catch {
    return null;
  }
}

export default async function ZeroPromptPage() {
  const initialSession = await getInitialSession();
  return (
    <Suspense fallback={<div className="min-h-screen bg-background p-4 text-foreground sm:p-6 lg:p-8"><div className="mx-auto max-w-[1600px]"><p className="text-sm text-muted-foreground">Loading Zero-Prompt workspace...</p></div></div>}>
      <ZeroPromptWorkspace initialSession={initialSession} />
    </Suspense>
  );
}
