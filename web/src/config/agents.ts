/**
 * Centralized agent definitions
 * Single source of truth for all agent metadata across the application
 */

export type AgentKey = "architect" | "scout" | "guardian" | "catalyst" | "advocate" | "strategist";

export type AgentColor = "amber" | "blue" | "emerald" | "purple" | "rose" | "slate";

export interface AgentDefinition {
  key: AgentKey;
  name: string;
  role: string;
  emoji: string;
  color: AgentColor;
  /** Full Tailwind color classes for borders/backgrounds/text */
  colorClasses: string;
  /** Gradient classes for card backgrounds */
  gradient: string;
}

export const AGENTS = [
  {
    key: "architect",
    name: "Architect",
    role: "Technical Lead",
    emoji: "🏗️",
    color: "amber",
    colorClasses: "border-amber-400/40 bg-amber-500/10 text-amber-200",
    gradient: "from-amber-500/20 to-amber-600/5",
  },
  {
    key: "scout",
    name: "Scout",
    role: "Market Analyst",
    emoji: "🔭",
    color: "blue",
    colorClasses: "border-blue-400/40 bg-blue-500/10 text-blue-200",
    gradient: "from-blue-500/20 to-blue-600/5",
  },
  {
    key: "guardian",
    name: "Guardian",
    role: "Risk Assessor",
    emoji: "🛡️",
    color: "emerald",
    colorClasses: "border-emerald-400/40 bg-emerald-500/10 text-emerald-200",
    gradient: "from-emerald-500/20 to-emerald-600/5",
  },
  {
    key: "catalyst",
    name: "Catalyst",
    role: "Innovation Officer",
    emoji: "⚡",
    color: "purple",
    colorClasses: "border-purple-400/40 bg-purple-500/10 text-purple-200",
    gradient: "from-purple-500/20 to-purple-600/5",
  },
  {
    key: "advocate",
    name: "Advocate",
    role: "UX Champion",
    emoji: "🎯",
    color: "rose",
    colorClasses: "border-rose-400/40 bg-rose-500/10 text-rose-200",
    gradient: "from-rose-500/20 to-rose-600/5",
  },
  {
    key: "strategist",
    name: "Strategist",
    role: "Session Lead",
    emoji: "🧭",
    color: "slate",
    colorClasses: "border-slate-400/40 bg-slate-500/10 text-slate-200",
    gradient: "from-slate-500/20 to-slate-600/5",
  },
] as const satisfies readonly AgentDefinition[];

/** Map of agent key to definition for O(1) lookup */
export const AGENT_MAP: Record<AgentKey, AgentDefinition> = {
  architect: AGENTS[0],
  scout: AGENTS[1],
  guardian: AGENTS[2],
  catalyst: AGENTS[3],
  advocate: AGENTS[4],
  strategist: AGENTS[5],
};

/**
 * Get agent definition by key
 * @param key - Agent key string (case-insensitive)
 * @returns AgentDefinition or null if not found
 */
export function getAgent(key: string): AgentDefinition | null {
  if (!key) return null;
  const normalized = key.toLowerCase();
  const agentKey = normalized as AgentKey;
  return AGENT_MAP[agentKey] ?? null;
}

/**
 * Convert string value to AgentKey
 * @param value - String that may contain agent name
 * @returns AgentKey or null if not found
 */
export function toAgentKey(value: string | undefined): AgentKey | null {
  if (!value) return null;
  const normalized = value.toLowerCase();
  if (normalized.includes("architect")) return "architect";
  if (normalized.includes("scout")) return "scout";
  if (normalized.includes("guardian")) return "guardian";
  if (normalized.includes("catalyst")) return "catalyst";
  if (normalized.includes("advocate")) return "advocate";
  if (normalized.includes("strategist")) return "strategist";
  return null;
}
