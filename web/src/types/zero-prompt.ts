export type CardStatus = "analyzing" | "go_ready" | "build_queued" | "building" | "deployed" | "nogo" | "passed" | "build_failed";

export interface ZPScoreBreakdown {
  proposal_clarity_weight?: number;
  execution_feasibility_weight?: number;
  market_viability_weight?: number;
  mvp_differentiation_weight?: number;
  evidence_strength_weight?: number;
  originality_signal?: number;
  originality_threshold?: number;
  proposal_clarity_signal?: number;
  execution_feasibility_signal?: number;
  market_viability_signal?: number;
  mvp_differentiation_signal?: number;
  evidence_strength_signal?: number;
  proposal_clarity_points?: number;
  execution_feasibility_points?: number;
  market_viability_points?: number;
  mvp_differentiation_points?: number;
  evidence_strength_points?: number;
  final_score?: number;
}

export interface ZPCard {
  card_id: string;
  video_id: string;
  title: string;
  status: CardStatus;
  score: number;
  reason?: string;
  reason_code?: string;
  score_breakdown?: ZPScoreBreakdown;
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
  build_phase?: string;
  build_node?: string;
  video_summary?: string;
  insights?: string[];
  mvp_proposal?: {
    app_name?: string;
    target_user?: string;
    problem_statement?: string;
    core_feature?: string;
    differentiation?: string;
    validation_signal?: string;
    tech_stack?: string;
    key_pages?: string[];
    not_in_scope?: string[];
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
