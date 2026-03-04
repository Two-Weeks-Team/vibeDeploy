"use client";

/**
 * MeetingView — The main live meeting container.
 * Shows council members in a circular/grid layout with speech bubbles.
 * Manages SSE connection and distributes events to child components.
 * TODO (Wave 5): SSE connection, phase state machine, speech rendering.
 */

export function MeetingView({ meetingId }: { meetingId: string }) {
  return (
    <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
      MeetingView for {meetingId} — stub
    </div>
  );
}
