const AGENT_URL =
  process.env.NEXT_PUBLIC_AGENT_URL ?? "http://localhost:8080";

export async function startMeeting(input: string): Promise<{
  meetingId: string;
  streamUrl: string;
}> {
  const meetingId = crypto.randomUUID();

  const response = await fetch(`${AGENT_URL}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: input,
      config: { configurable: { thread_id: meetingId } },
    }),
  });

  if (!response.ok) {
    throw new Error(`Agent returned ${response.status}`);
  }

  return {
    meetingId,
    streamUrl: `${AGENT_URL}/run`,
  };
}

export async function resumeMeeting(
  meetingId: string,
  action: string = "proceed",
): Promise<Response> {
  const response = await fetch(`${AGENT_URL}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: meetingId, action }),
  });

  if (!response.ok) {
    throw new Error(`Resume returned ${response.status}`);
  }

  return response;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${AGENT_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

export type MeetingResult = {
  score: number;
  verdict: "GO" | "CONDITIONAL" | "NO-GO";
  analyses: Record<string, unknown>[];
  debates: Record<string, unknown>[];
  documents: Record<string, unknown>[];
  deployment?: {
    repoUrl: string;
    liveUrl: string;
  };
};

export async function getMeetingResult(
  meetingId: string,
): Promise<MeetingResult | null> {
  try {
    const response = await fetch(`${AGENT_URL}/result/${meetingId}`);
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}
