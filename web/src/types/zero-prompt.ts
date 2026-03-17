export type CardStatus = "analyzing" | "go_ready" | "build_queued" | "building" | "deployed" | "nogo" | "passed" | "build_failed";

export interface ZPCard {
  card_id: string;
  video_id: string;
  title: string;
  status: CardStatus;
  score: number;
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
