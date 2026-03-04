"use client";

/**
 * CouncilMember — Individual agent card with avatar, name, role, and speech bubble.
 * Shows current speaking state, analysis progress, and score.
 * TODO (Wave 5): Speech bubble animation, typing indicator, score display.
 */

interface CouncilMemberProps {
  name: string;
  emoji: string;
  role: string;
  isSpeaking?: boolean;
  message?: string;
  score?: number;
}

export function CouncilMember({
  name,
  emoji,
  role,
  isSpeaking = false,
  message,
  score,
}: CouncilMemberProps) {
  return (
    <div className="rounded-lg border p-4 text-center">
      <div className="text-3xl">{emoji}</div>
      <p className="mt-1 font-medium">{name}</p>
      <p className="text-xs text-muted-foreground">{role}</p>
      {isSpeaking && (
        <p className="mt-2 text-sm">{message ?? "..."}</p>
      )}
      {score !== undefined && (
        <p className="mt-1 text-sm font-bold">{score}/100</p>
      )}
    </div>
  );
}
