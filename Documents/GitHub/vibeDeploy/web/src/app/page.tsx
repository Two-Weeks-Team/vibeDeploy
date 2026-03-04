"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function LandingPage() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    setIsLoading(true);

    // TODO: POST to agent API, get meeting ID, redirect
    // const { meetingId } = await startMeeting(input);
    // router.push(`/meeting/${meetingId}`);

    // Placeholder: simulate redirect
    const mockId = crypto.randomUUID();
    router.push(`/meeting/${mockId}`);
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="w-full max-w-2xl space-y-8">
        {/* Hero */}
        <div className="space-y-4 text-center">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            vibeDeploy
          </h1>
          <p className="text-lg text-muted-foreground">
            One sentence. One meeting. One live app.
          </p>
        </div>

        {/* Input Form */}
        <Card>
          <CardHeader>
            <CardTitle>Describe your app idea</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <Textarea
                placeholder="I want a restaurant queue management app with QR codes... or paste a YouTube URL"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                rows={4}
                className="resize-none"
              />
              <Button
                type="submit"
                className="w-full"
                disabled={!input.trim() || isLoading}
              >
                {isLoading ? "Convening The Vibe Council..." : "Start Meeting"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Council Preview */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {[
            { emoji: "🏗️", name: "Architect", role: "Technical Lead" },
            { emoji: "🔭", name: "Scout", role: "Market Analyst" },
            { emoji: "🛡️", name: "Guardian", role: "Risk Assessor" },
            { emoji: "⚡", name: "Catalyst", role: "Innovation Officer" },
            { emoji: "🎯", name: "Advocate", role: "UX Champion" },
            { emoji: "🧭", name: "Strategist", role: "Session Lead" },
          ].map((agent) => (
            <Card key={agent.name} className="text-center">
              <CardContent className="pt-4">
                <div className="text-2xl">{agent.emoji}</div>
                <p className="mt-1 text-sm font-medium">{agent.name}</p>
                <p className="text-xs text-muted-foreground">{agent.role}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
