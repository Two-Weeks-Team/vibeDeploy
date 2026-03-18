"use client";

import Link from "next/link";
import { useState } from "react";
import { Rocket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ZeroPromptLanding } from "@/components/zero-prompt-landing";

const DEFAULT_VIDEO_URL = "https://www.youtube.com/watch?v=aADukThvjXQ";

export default function LandingPage() {
  const [youtubeUrl, setYoutubeUrl] = useState(DEFAULT_VIDEO_URL);

  return (
    <ZeroPromptLanding
      youtubeUrl={youtubeUrl}
      onYoutubeUrlChange={setYoutubeUrl}
      startAction={
        <Link href="/zero-prompt?autostart=true">
          <Button size="lg" className="h-14 px-8 text-lg font-bold gap-2 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600">
            <Rocket className="w-5 h-5" />
            Zero-Prompt Start
          </Button>
        </Link>
      }
    />
  );
}
