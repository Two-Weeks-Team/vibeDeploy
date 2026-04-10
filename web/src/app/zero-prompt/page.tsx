import { DASHBOARD_API_URL } from "@/lib/api";
import { authenticatedFetch } from "@/lib/fetch-with-auth";
import { ZeroPromptWorkspace } from "@/components/zero-prompt/zero-prompt-workspace";
import type { ZPSession } from "@/types/zero-prompt";

async function getInitialSession(): Promise<ZPSession | null> {
  try {
    const response = await authenticatedFetch(`${DASHBOARD_API_URL}/zero-prompt/dashboard`, { cache: "no-store" });
    if (!response.ok) return null;
    const data = await response.json();
    if (!data?.session_id) return null;
    return data as ZPSession;
  } catch {
    return null;
  }
}

export default async function ZeroPromptPage({ searchParams }: { searchParams?: Promise<Record<string, string | string[] | undefined>> }) {
  const [session, resolvedSearchParams] = await Promise.all([
    getInitialSession(),
    searchParams ?? Promise.resolve({} as Record<string, string | string[] | undefined>),
  ]);
  const autostartParam = resolvedSearchParams?.autostart;
  const autostart = Array.isArray(autostartParam) ? autostartParam.includes("true") : autostartParam === "true";

  return <ZeroPromptWorkspace initialSession={session} autostart={autostart} />;
}
