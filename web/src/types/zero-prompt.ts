export type CardStatus = "analyzing" | "go_ready" | "build_queued" | "building" | "deployed" | "nogo" | "passed" | "build_failed";

export interface ZPCard {
  card_id: string;
  video_id: string;
  title: string;
  status: CardStatus;
  score: number;
  reason?: string;
  reason_code?: string;
  domain?: string;
  papers_found?: number;
  competitors_found?: string;
  saturation?: string;
  novelty_boost?: number;
  thread_id?: string | null;
  build_step?: string;
  analysis_step?: string;
  repo_url?: string;
  live_url?: string;
  video_summary?: string;
  insights?: string[];
  mvp_proposal?: {
    app_name?: string;
    core_feature?: string;
    tech_stack?: string;
    key_pages?: string[];
    estimated_days?: number;
  };
}

export interface ZPSession {
  session_id: string;
  status: "exploring" | "paused" | "completed";
  cards: ZPCard[];
}

export interface ZPAction {
  type: string;
  timestamp: string;
  message: string;
}
