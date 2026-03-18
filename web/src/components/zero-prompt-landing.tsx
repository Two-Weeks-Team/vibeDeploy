"use client";

import type { ReactNode, Ref } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Code2, ExternalLink, FlaskConical, Globe, LayoutDashboard, Lock, Play, Youtube } from "lucide-react";

function extractVideoId(url: string): string | null {
  try {
    const u = new URL(url);
    const rawId = u.hostname.includes("youtube.com") ? u.searchParams.get("v") : u.hostname === "youtu.be" ? u.pathname.slice(1) : null;
    if (!rawId || rawId.length < 11) return null;
    return rawId.slice(0, 11);
  } catch {}
  return null;
}

const COUNCIL_AGENTS = [
  { emoji: "🏗️", name: "Architect", role: "Technical Lead" },
  { emoji: "🔭", name: "Scout", role: "Market Analyst" },
  { emoji: "🛡️", name: "Guardian", role: "Risk Assessor" },
  { emoji: "⚡", name: "Catalyst", role: "Innovation Officer" },
  { emoji: "🎯", name: "Advocate", role: "UX Champion" },
  { emoji: "🧭", name: "Strategist", role: "Session Lead" },
];

const STEPS = [
  { num: "1", title: "Discover", desc: "AI explores YouTube for trending app ideas", icon: Youtube },
  { num: "2", title: "Evaluate", desc: "Vibe Council scores feasibility with 6 agents", icon: FlaskConical },
  { num: "3", title: "Build", desc: "PRD, code, and assets auto-generated", icon: Code2 },
  { num: "4", title: "Deploy", desc: "Live app on DigitalOcean in minutes", icon: Globe },
];

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

const cardItem = {
  hidden: { opacity: 0, y: 16, scale: 0.95 },
  visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.35, ease: "easeOut" as const } },
};

type ZeroPromptLandingProps = {
  youtubeUrl: string;
  onYoutubeUrlChange: (value: string) => void;
  startAction: ReactNode;
  inputRef?: Ref<HTMLInputElement>;
};

export function ZeroPromptLanding({ youtubeUrl, onYoutubeUrlChange, startAction, inputRef }: ZeroPromptLandingProps) {
  const videoId = extractVideoId(youtubeUrl);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-16 relative">
      <div className="absolute top-4 right-4">
        <Link href="/dashboard">
          <Button variant="outline" size="sm" className="gap-2">
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </Button>
        </Link>
      </div>

      <div className="w-full max-w-2xl space-y-12">
        <motion.div className="space-y-4 text-center" initial="hidden" animate="visible" variants={containerVariants}>
          <motion.h1 variants={fadeUp} className="text-5xl font-bold tracking-tight sm:text-6xl bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            vibeDeploy
          </motion.h1>
          <motion.p variants={fadeUp} className="text-xl text-muted-foreground">
            Zero prompts. Zero coding. One button deploys a live app.
          </motion.p>
          <motion.p variants={fadeUp} className="text-sm text-muted-foreground/70">
            AI discovers ideas from YouTube, validates with research, writes code, and ships to DigitalOcean — autonomously.
          </motion.p>
          <motion.div variants={fadeUp} className="flex flex-col items-center gap-4 pt-6">
            <div className="flex flex-col sm:flex-row items-center gap-3">
              {startAction}
              <div className="group/demo relative">
                <Link href="/demo">
                  <Button size="lg" variant="outline" className="h-14 px-8 text-lg font-semibold gap-2 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300">
                    <Play className="w-5 h-5 fill-current" />
                    Watch Demo
                  </Button>
                </Link>
                <div className="pointer-events-none absolute top-full left-1/2 z-20 mt-3 w-[min(90vw,26rem)] -translate-x-1/2 rounded-2xl border border-emerald-500/20 bg-background/95 p-4 text-left shadow-2xl shadow-black/30 opacity-0 backdrop-blur-sm transition-all duration-200 -translate-y-2 group-hover/demo:pointer-events-auto group-hover/demo:translate-y-0 group-hover/demo:opacity-100 group-focus-within/demo:pointer-events-auto group-focus-within/demo:translate-y-0 group-focus-within/demo:opacity-100">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-300">For judges & competitors</span>
                      <span className="rounded-full border border-border/60 px-2.5 py-1 text-xs text-muted-foreground">No setup</span>
                      <span className="rounded-full border border-border/60 px-2.5 py-1 text-xs text-muted-foreground">Autoplay</span>
                      <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-300">8x accelerated</span>
                    </div>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      The demo compresses the real pipeline to about <span className="font-medium text-foreground">8x speed</span> so reviewers can understand discovery, council review, GO approval, build, and deploy without waiting through the full runtime.
                    </p>
                    <div className="grid gap-2 sm:grid-cols-3">
                      <div className="space-y-1">
                        <p className="text-sm font-semibold">1. Open Demo</p>
                        <p className="text-xs leading-relaxed text-muted-foreground">Watch the YouTube URL type in and the preview update.</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-semibold">2. Watch the AI pick</p>
                        <p className="text-xs leading-relaxed text-muted-foreground">The council opens the card, then visibly approves the GO handoff.</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-semibold">3. See the outcome</p>
                        <p className="text-xs leading-relaxed text-muted-foreground">The demo builds, deploys, and clicks into the shipped app.</p>
                      </div>
                    </div>
                  </div>
                  <div className="absolute bottom-full left-1/2 h-3 w-3 -translate-x-1/2 translate-y-1/2 rotate-45 border border-emerald-500/20 border-r-0 border-b-0 bg-background/95" />
                </div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">Press Start for the full Zero-Prompt loop, or open Demo for a guided autoplay judge flow.</p>
          </motion.div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.5 }}>
          <div className="relative my-10">
            <div className="absolute inset-0 flex items-center" aria-hidden="true">
              <div className="w-full border-t border-border/50" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-background px-4 text-sm text-muted-foreground">Or start from a YouTube video</span>
            </div>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35, duration: 0.5 }}>
          <Card className="border-border/50 overflow-hidden">
            <CardContent className="pt-6 space-y-4">
              <div className="flex gap-2">
                <Input
                  ref={inputRef}
                  value={youtubeUrl}
                  onChange={(e) => onYoutubeUrlChange(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  className="font-mono text-sm"
                />
                <Button
                  className="shrink-0 gap-2 bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400"
                  onClick={() => alert("This feature is restricted to admin users and authorized IPs only.")}
                >
                  <Lock className="w-4 h-4" />
                  Start
                </Button>
              </div>

              {videoId && (
                <a href={youtubeUrl} target="_blank" rel="noopener noreferrer" className="block group">
                  <div className="flex items-center gap-2 mb-2">
                    <Youtube className="w-5 h-5 text-red-500" />
                    <span className="text-sm font-medium">YouTube</span>
                  </div>
                  <p className="text-sm text-blue-400 group-hover:underline mb-3 flex items-center gap-1">
                    {youtubeUrl}
                    <ExternalLink className="w-3 h-3" />
                  </p>
                  <div className="relative aspect-video rounded-lg overflow-hidden bg-muted">
                    <Image
                      src={`https://img.youtube.com/vi/${videoId}/hqdefault.jpg`}
                      alt="YouTube video thumbnail"
                      fill
                      className="object-cover"
                      unoptimized
                    />
                    <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/30 transition-colors">
                      <div className="w-16 h-16 rounded-full bg-black/60 flex items-center justify-center">
                        <Play className="w-8 h-8 text-white fill-white ml-1" />
                      </div>
                    </div>
                  </div>
                </a>
              )}

              {!videoId && youtubeUrl.length > 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">
                  Paste a valid YouTube URL to see the preview.
                </p>
              )}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4, duration: 0.5 }}>
          <div className="relative my-10">
            <div className="absolute inset-0 flex items-center" aria-hidden="true">
              <div className="w-full border-t border-border/50" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-background px-4 text-sm text-muted-foreground">How it works</span>
            </div>
          </div>
        </motion.div>

        <motion.div className="grid grid-cols-2 gap-4 sm:grid-cols-4" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.1, delayChildren: 0.45 } } }}>
          {STEPS.map((step) => {
            const Icon = step.icon;
            return (
              <motion.div key={step.num} variants={fadeUp}>
                <Card className="text-center border-border/50 h-full">
                  <CardContent className="pt-5 space-y-2">
                    <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                      <Icon className="w-5 h-5 text-primary" />
                    </div>
                    <p className="text-sm font-semibold">{step.title}</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">{step.desc}</p>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </motion.div>

        <motion.div className="grid grid-cols-2 gap-3 sm:grid-cols-3" initial="hidden" animate="visible" variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.08, delayChildren: 0.6 } } }}>
          {COUNCIL_AGENTS.map((agent) => (
            <motion.div key={agent.name} variants={cardItem} whileHover={{ scale: 1.05, y: -2 }} transition={{ type: "spring", stiffness: 400, damping: 20 }}>
              <Card className="text-center transition-shadow hover:shadow-lg hover:shadow-primary/5 border-border/50">
                <CardContent className="pt-4">
                  <div className="text-2xl">{agent.emoji}</div>
                  <p className="mt-1 text-sm font-medium">{agent.name}</p>
                  <p className="text-xs text-muted-foreground">{agent.role}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
