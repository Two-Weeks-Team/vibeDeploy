import { Card, CardContent } from "@/components/ui/card";
import { InputForm } from "@/components/input-form";

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

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-2xl space-y-12">
        <div className="space-y-4 text-center">
          <h1 className="text-5xl font-bold tracking-tight sm:text-6xl bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            vibeDeploy
          </h1>
          <p className="text-xl text-muted-foreground">
            From idea to live app — one sentence, one meeting.
          </p>
          <p className="text-sm text-muted-foreground/70">
            Describe your app idea. The Vibe Council debates feasibility, then builds and deploys it.
          </p>
        </div>

        <InputForm />

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {STEPS.map((step) => (
            <div key={step.num} className="text-center space-y-1">
              <div className="mx-auto flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
                {step.num}
              </div>
              <p className="text-sm font-medium">{step.title}</p>
              <p className="text-xs text-muted-foreground">{step.desc}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {COUNCIL_AGENTS.map((agent) => (
            <Card key={agent.name} className="text-center transition-shadow hover:shadow-lg border-border/50">
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
