"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { startMeeting, startBrainstorm } from "@/lib/api";

const YOUTUBE_RE = /(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/;

export function InputForm() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isBrainstorming, setIsBrainstorming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const youtubeMatch = useMemo(() => YOUTUBE_RE.exec(input), [input]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!input.trim()) {
      setError("Please describe your app idea or paste a YouTube URL.");
      return;
    }

    setIsLoading(true);
    try {
      const { meetingId } = await startMeeting(input);
      router.push(`/meeting/${meetingId}`);
    } catch {
      setError("Failed to start meeting. Please try again.");
      setIsLoading(false);
    }
  }

  async function handleBrainstorm() {
    setError(null);

    if (!input.trim()) {
      setError("Please describe your app idea or paste a YouTube URL.");
      return;
    }

    setIsBrainstorming(true);
    try {
      const { sessionId } = await startBrainstorm(input);
      router.push(`/brainstorm/${sessionId}`);
    } catch {
      setError("Failed to start brainstorm. Please try again.");
      setIsBrainstorming(false);
    }
  }

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          Describe your app idea
          {youtubeMatch && (
            <Badge variant="secondary" className="text-xs">
              YouTube detected
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Textarea
            placeholder="I want a restaurant queue management app with QR codes... or paste a YouTube URL"
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              if (error) setError(null);
            }}
            rows={4}
            className={`resize-none bg-background/50 ${error ? "border-destructive" : ""}`}
          />
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button
              type="submit"
              className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-medium"
              disabled={!input.trim() || isLoading || isBrainstorming}
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Convening The Vibe Council...
                </span>
              ) : (
                "Start Meeting"
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              className="flex-1 border-purple-500/40 bg-gradient-to-r from-purple-500/10 to-amber-500/10 hover:from-purple-500/20 hover:to-amber-500/20 font-medium"
              disabled={!input.trim() || isLoading || isBrainstorming}
              onClick={handleBrainstorm}
            >
              {isBrainstorming ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-purple-400 border-t-transparent" />
                  Council brainstorming...
                </span>
              ) : (
                "Brainstorm Ideas"
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
