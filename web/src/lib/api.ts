/**
 * API Client — Helpers for communicating with the vibeDeploy agent backend.
 *
 * Agent is deployed on Gradient ADK and exposes:
 *   POST /run   — Start a new meeting (streaming SSE)
 *   GET  /health — Health check
 *
 * The agent URL is configured via NEXT_PUBLIC_AGENT_URL environment variable.
 *
 * TODO (Wave 5): Add typed request/response interfaces, error handling,
 * retry logic, and session management.
 */

const AGENT_URL =
  process.env.NEXT_PUBLIC_AGENT_URL ?? "http://localhost:8080";

/** Start a new Vibe Council meeting. Returns the SSE stream URL and meeting ID. */
export async function startMeeting(input: string): Promise<{
  meetingId: string;
  streamUrl: string;
}> {
  // TODO: Implement actual API call
  // The agent's POST /run accepts { input: string } and streams SSE events.
  // For now, return a mock.
  const meetingId = crypto.randomUUID();
  return {
    meetingId,
    streamUrl: `${AGENT_URL}/run`,
  };
}

/** Check if the agent is healthy. */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${AGENT_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

/** Get the result of a completed meeting. */
export async function getMeetingResult(meetingId: string): Promise<{
  score: number;
  verdict: "GO" | "CONDITIONAL" | "NO-GO";
  analyses: Record<string, unknown>[];
  debates: Record<string, unknown>[];
  documents: Record<string, unknown>[];
  deployment?: {
    repoUrl: string;
    liveUrl: string;
  };
} | null> {
  // TODO: Implement actual API call — may need a separate endpoint
  // or fetch from database via a GET endpoint.
  return null;
}
