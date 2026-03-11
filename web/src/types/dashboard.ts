export interface AgentAnalysis {
  agent: string;
  score: number;
  reasoning: string;
  findings: string[];
  key_findings?: string[];
}

export interface ScoringBreakdown {
  technical_feasibility?: { score: number; reasoning: string; key_findings: string[] };
  market_viability?: { score: number; reasoning: string; key_findings: string[] };
  innovation_score?: { score: number; reasoning: string; key_findings: string[] };
  risk_profile?: { score: number; reasoning: string; key_findings: string[] };
  user_impact?: { score: number; reasoning: string; key_findings: string[] };
  final_score: number;
  decision: "GO" | "CONDITIONAL" | "NO_GO";
}

export interface DebateEntry {
  topic: string;
  [key: string]: unknown;
}

export interface DocumentEntry {
  type: string;
  content: string;
}

export interface DeployedApp {
  thread_id: string;
  score: number;
  verdict: VerdictType;
  input_prompt: string;
  idea_summary: string;
  deployment: {
    repoUrl: string;
    liveUrl: string;
    status?: string;
    ciStatus?: string;
  };
  created_at: string;
}

export interface MeetingResultFull {
  thread_id: string;
  score: number;
  verdict: "GO" | "CONDITIONAL" | "NO-GO";
  analyses: AgentAnalysis[];
  scoring: ScoringBreakdown;
  debates: DebateEntry[];
  documents: DocumentEntry[];
  deployment?: { repoUrl: string; liveUrl: string };
  input_prompt?: string;
  idea_summary?: string;
  created_at: string;
}

export interface BrainstormResultFull {
  thread_id: string;
  insights: Array<{
    agent: string;
    ideas: Array<{ title: string; description: string }>;
    opportunities: string[];
    wild_card: string;
    action_items: string[];
  }>;
  synthesis: {
    themes: string[];
    top_ideas: Array<{ title: string; description: string; source_agent: string }>;
    synergies: string[];
    recommended_direction: string;
    quick_wins: string[];
  };
  idea: Record<string, unknown>;
  idea_summary: string;
  created_at: string;
}

export interface ActivePipeline {
  thread_id: string;
  type: "evaluation" | "brainstorm";
  phase: string;
  started_at: number;
  prompt_preview: string;
}

export interface DashboardStats {
  total_meetings: number;
  total_brainstorms: number;
  avg_score: number;
  go_count: number;
  nogo_count: number;
}

export interface DashboardEvent {
  type: string;
  thread_id: string;
  phase?: string;
  node?: string;
  message?: string;
  agent?: string;
  axis?: string;
  stage?: string;
  score?: number;
  final_score?: number;
  decision?: string;
  [key: string]: unknown;
}

export type PipelineNodeStatus = "idle" | "active" | "complete" | "error";

export interface ScoreDistributionBin {
  range: string;
  count: number;
  color: string;
}

export interface AgentPerformance {
  agent: string;
  avgScore: number;
  count: number;
}

export type VerdictType = "GO" | "CONDITIONAL" | "NO-GO";
