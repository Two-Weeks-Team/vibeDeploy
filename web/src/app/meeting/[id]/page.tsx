"use client";

import { useParams } from "next/navigation";
import { MeetingView } from "@/components/meeting-view";

export default function MeetingPage() {
  const params = useParams<{ id: string }>();

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.16),transparent_42%),radial-gradient(circle_at_bottom_right,rgba(34,197,94,0.16),transparent_42%)] px-4 py-8 md:px-6">
      <div className="mx-auto w-full max-w-[1680px] space-y-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">The Vibe Council</h1>
          <p className="text-sm text-muted-foreground md:text-base">Live council meeting in progress.</p>
          <p className="text-xs text-muted-foreground/80">Session: {params.id}</p>
        </div>

        <MeetingView meetingId={params.id} />
      </div>
    </div>
  );
}
