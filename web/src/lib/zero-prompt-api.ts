import { DASHBOARD_API_URL } from "./api";
import type { ZPSession } from "@/types/zero-prompt";

function parseStartSessionResponse(raw: string): ZPSession {
  const trimmed = raw.trim();
  if (!trimmed) throw new Error("Empty start session response");
  if (trimmed.startsWith("{")) return JSON.parse(trimmed) as ZPSession;

  for (const line of trimmed.split(/\r?\n/)) {
    if (!line.startsWith("data: ")) continue;
    const payload = JSON.parse(line.slice(6));
    if (payload.type === "zp.session.start") {
      return {
        session_id: String(payload.session_id),
        status: String(payload.session_status || "exploring"),
        goal_go_cards: Number(payload.goal_go_cards || 0),
        cards: [],
        build_queue: [],
        active_build: null,
      } as ZPSession;
    }
  }

  throw new Error("No zp.session.start event found");
}

export async function startSession(goal?: number): Promise<ZPSession> {
  const response = await fetch(`${DASHBOARD_API_URL}/zero-prompt/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
  });
  if (!response.ok) throw new Error("Failed to start session");
  return parseStartSessionResponse(await response.text());
}

export async function getDashboard(): Promise<ZPSession & { session_id: string | null }> {
  const response = await fetch(`${DASHBOARD_API_URL}/zero-prompt/dashboard`);
  if (!response.ok) throw new Error("Failed to get dashboard");
  return response.json();
}

export async function getSession(id: string): Promise<ZPSession> {
  const response = await fetch(`${DASHBOARD_API_URL}/zero-prompt/${id}`);
  if (!response.ok) throw new Error("Failed to get session");
  return response.json();
}

export async function queueBuild(sessionId: string, cardId: string): Promise<void> {
  const response = await fetch(`${DASHBOARD_API_URL}/zero-prompt/${sessionId}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "queue_build", card_id: cardId }),
  });
  if (!response.ok) throw new Error("Failed to queue build");
}

export async function passCard(sessionId: string, cardId: string): Promise<void> {
  const response = await fetch(`${DASHBOARD_API_URL}/zero-prompt/${sessionId}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "pass_card", card_id: cardId }),
  });
  if (!response.ok) throw new Error("Failed to pass card");
}

export async function deleteCard(sessionId: string, cardId: string): Promise<void> {
  const response = await fetch(`${DASHBOARD_API_URL}/zero-prompt/${sessionId}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "delete_card", card_id: cardId }),
  });
  if (!response.ok) throw new Error("Failed to delete card");
}

export function getBuildEventsUrl(sessionId: string, cardId: string): string {
  return `${DASHBOARD_API_URL}/zero-prompt/${sessionId}/build/${cardId}/events`;
}
