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
  code_files?: Array<{ path: string; content: string; language: string; source: string }>;
  deployment?: {
    repoUrl: string;
    liveUrl: string;
    status?: string;
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

export async function startBrainstorm(input: string): Promise<{
  sessionId: string;
  streamUrl: string;
}> {
  const sessionId = crypto.randomUUID();
  const response = await fetch(`${AGENT_URL}/brainstorm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: input,
      config: { configurable: { thread_id: sessionId } },
    }),
  });
  if (!response.ok) throw new Error(`Agent returned ${response.status}`);
  return { sessionId, streamUrl: `${AGENT_URL}/brainstorm` };
}

export type BrainstormResult = {
  insights: Array<{
    agent: string;
    ideas: Array<{ title: string; description: string }>;
    opportunities: string[];
    wild_card: string;
    action_items: string[];
  }>;
  synthesis: {
    themes: string[];
    top_ideas: Array<{
      title: string;
      description: string;
      source_agent: string;
    }>;
    synergies: string[];
    recommended_direction: string;
    quick_wins: string[];
  };
  idea: Record<string, unknown>;
  idea_summary: string;
};

export async function getBrainstormResult(
  sessionId: string,
): Promise<BrainstormResult | null> {
  try {
    const response = await fetch(
      `${AGENT_URL}/brainstorm/result/${sessionId}`,
    );
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export async function getDashboardStats(): Promise<{
  total_meetings: number;
  total_brainstorms: number;
  avg_score: number;
  go_count: number;
  nogo_count: number;
}> {
  try {
    const response = await fetch(`${AGENT_URL}/dashboard/stats`);
    if (!response.ok) throw new Error("Failed to fetch stats");
    return response.json();
  } catch {
    return {
      total_meetings: 0,
      total_brainstorms: 0,
      avg_score: 0,
      go_count: 0,
      nogo_count: 0,
    };
  }
}

export async function getDashboardResults(): Promise<
  Array<{
    thread_id: string;
    score: number;
    verdict: string;
    created_at: string;
  }>
> {
  try {
    const response = await fetch(`${AGENT_URL}/dashboard/results`);
    if (!response.ok) throw new Error("Failed to fetch results");
    return response.json();
  } catch {
    return [];
  }
}

export async function getDashboardBrainstorms(): Promise<
  Array<{
    thread_id: string;
    created_at: string;
  }>
> {
  try {
    const response = await fetch(`${AGENT_URL}/dashboard/brainstorms`);
    if (!response.ok) throw new Error("Failed to fetch brainstorms");
    return response.json();
  } catch {
    return [];
  }
}
