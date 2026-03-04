"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { startMeeting } from "@/lib/api";

const YOUTUBE_RE = /(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/;

export function InputForm() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
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
          <Button
            type="submit"
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-medium"
            disabled={!input.trim() || isLoading}
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
        </form>
      </CardContent>
    </Card>
  );
}
