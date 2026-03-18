"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { InputForm } from "@/components/input-form";
import { Button } from "@/components/ui/button";
import { Rocket } from "lucide-react";

const COUNCIL_AGENTS = [
  { emoji: "🏗️", name: "Architect", role: "Technical Lead" },
  { emoji: "🔭", name: "Scout", role: "Market Analyst" },
  { emoji: "🛡️", name: "Guardian", role: "Risk Assessor" },
  { emoji: "⚡", name: "Catalyst", role: "Innovation Officer" },
  { emoji: "🎯", name: "Advocate", role: "UX Champion" },
  { emoji: "🧭", name: "Strategist", role: "Session Lead" },
];

const STEPS = [
  { num: "1", title: "Describe", desc: "Enter your idea or paste a YouTube URL" },
  { num: "2", title: "Council", desc: "6 AI agents debate feasibility live" },
  { num: "3", title: "Build", desc: "PRD, code, and assets generated" },
  { num: "4", title: "Deploy", desc: "Live app on DigitalOcean in minutes" },
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

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-16 relative">
      <div className="absolute top-4 right-4">
        <Link href="/dashboard">
          <Button variant="outline" size="sm" className="gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><title>Dashboard</title><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>
            Dashboard
          </Button>
        </Link>
      </div>
      <div className="w-full max-w-2xl space-y-12">
        <motion.div
          className="space-y-4 text-center"
          initial="hidden"
          animate="visible"
          variants={containerVariants}
        >
          <motion.h1
            variants={fadeUp}
            className="text-5xl font-bold tracking-tight sm:text-6xl bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent"
          >
            vibeDeploy
          </motion.h1>
          <motion.p variants={fadeUp} className="text-xl text-muted-foreground">
            From idea to live app — one sentence, one meeting.
          </motion.p>
          <motion.p variants={fadeUp} className="text-sm text-muted-foreground/70">
            Describe your app idea. The Vibe Council debates feasibility, then builds and deploys it.
          </motion.p>
          <motion.div variants={fadeUp} className="flex flex-col items-center gap-3 pt-6">
            <Link href="/zero-prompt?autostart=true">
              <Button size="lg" className="h-14 px-8 text-lg font-bold gap-2 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600">
                <Rocket className="w-5 h-5" />
                Zero-Prompt Start
              </Button>
            </Link>
            <p className="text-xs text-muted-foreground">Press Start. AI discovers, validates, and deploys apps autonomously.</p>
          </motion.div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.5 }}>
          <div className="relative mb-8">
            <div className="absolute inset-0 flex items-center" aria-hidden="true">
              <div className="w-full border-t border-border/50" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-background px-4 text-sm text-muted-foreground">Or describe your idea</span>
            </div>
          </div>
          <InputForm />
        </motion.div>

        <motion.div
          className="grid grid-cols-2 gap-3 sm:grid-cols-4"
          initial="hidden"
          animate="visible"
          variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.1, delayChildren: 0.45 } } }}
        >
          {STEPS.map((step) => (
            <motion.div key={step.num} variants={fadeUp} className="text-center space-y-1">
              <div className="mx-auto flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
                {step.num}
              </div>
              <p className="text-sm font-medium">{step.title}</p>
              <p className="text-xs text-muted-foreground">{step.desc}</p>
            </motion.div>
          ))}
        </motion.div>

        <motion.div
          className="grid grid-cols-2 gap-3 sm:grid-cols-3"
          initial="hidden"
          animate="visible"
          variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.08, delayChildren: 0.6 } } }}
        >
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
