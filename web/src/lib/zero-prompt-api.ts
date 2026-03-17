import { DASHBOARD_API_URL } from "./api";
import type { ZPSession } from "@/types/zero-prompt";

export async function startSession(goal?: number): Promise<{ session_id: string }> {
  const response = await fetch(`${DASHBOARD_API_URL}/zero-prompt/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
  });
  if (!response.ok) throw new Error("Failed to start session");
  return response.json();
}

export async function getSession(id: string): Promise<ZPSession> {
  const response = await fetch(`${DASHBOARD_API_URL}/zero-prompt/${id}`);
  if (!response.ok) throw new Error("Failed to get session");
  return response.json();
}

export async function queueBuild(sessionId: string, cardId: string): Promise<void> {
  const response = await fetch(`${DASHBOARD_API_URL}/zero-prompt/${sessionId}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "queue_build", card_id: cardId }),
  });
  if (!response.ok) throw new Error("Failed to queue build");
}

export async function passCard(sessionId: string, cardId: string): Promise<void> {
  const response = await fetch(`${DASHBOARD_API_URL}/zero-prompt/${sessionId}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "pass", card_id: cardId }),
  });
  if (!response.ok) throw new Error("Failed to pass card");
}
