"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { animate } from "framer-motion";
import { motion } from "framer-motion";
import confetti from "canvas-confetti";
import { CodePreview } from "@/components/code-preview";
import { DeployStatus } from "@/components/deploy-status";
import { DocViewer } from "@/components/doc-viewer";
import { VibeScore } from "@/components/vibe-score";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getMeetingResult, type MeetingResult } from "@/lib/api";

function useAnimatedCounter(target: number, duration = 1.5) {
  const [display, setDisplay] = useState(0);
  const prevTarget = useRef(0);

  useEffect(() => {
    if (target === prevTarget.current) return;
    const controls = animate(prevTarget.current, target, {
      duration,
      ease: "easeOut" as const,
      onUpdate: (v) => setDisplay(Math.round(v)),
    });
    prevTarget.current = target;
    return () => controls.stop();
  }, [target, duration]);

  return display;
}

type Verdict = "GO" | "CONDITIONAL" | "NO-GO";

export default function ResultPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const [result, setResult] = useState<MeetingResult | null | undefined>(undefined);

  useEffect(() => {
    let mounted = true;

    getMeetingResult(params.id).then((next) => {
      if (mounted) setResult(next);
    });

    return () => {
      mounted = false;
    };
  }, [params.id]);

  const verdict = useMemo<Verdict>(() => normalizeVerdict(result?.verdict), [result?.verdict]);

  useEffect(() => {
    if (verdict !== "GO") return;
    confetti({ particleCount: 150, spread: 72, origin: { y: 0.22 } });
  }, [verdict]);

  if (result === undefined) {
    return <LoadingState meetingId={params.id} />;
  }

  if (result === null) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <Alert className="max-w-xl border-white/10">
          <AlertTitle>Result not found</AlertTitle>
          <AlertDescription className="mt-2">
            Meeting result for <span className="font-mono text-xs">{params.id}</span> is not available yet.
          </AlertDescription>
          <div className="mt-4">
            <Button onClick={() => router.push(`/meeting/${params.id}`)}>Back to Meeting</Button>
          </div>
        </Alert>
      </div>
    );
  }

  const score = Math.round(result.score);
  const analysisMap = extractAnalysisMap(result.analyses);

  const suggestions =
    verdict === "CONDITIONAL"
      ? [
          "Narrow the launch to one critical workflow.",
          "Defer advanced automations to post-launch iteration.",
          "Validate one target persona before scaling.",
        ]
      : [];

  const noGoReasons =
    verdict === "NO-GO"
      ? [
          "Technical complexity is too high for an MVP timeline.",
          "Risk profile outweighs immediate market confidence.",
          "Current scope lacks a tight, testable wedge.",
        ]
      : [];

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.18),transparent_40%),radial-gradient(circle_at_bottom_left,rgba(59,130,246,0.14),transparent_45%)] px-4 py-8 md:px-6">
      <motion.div
        className="mx-auto w-full max-w-[1440px] space-y-6"
        initial="hidden"
        animate="visible"
        variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.12 } } }}
      >
        <motion.div
          className="space-y-2"
          variants={{ hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } } }}
        >
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Council Result Dashboard</h1>
          <p className="text-sm text-muted-foreground md:text-base">Session {params.id}</p>
        </motion.div>

        <motion.div variants={{ hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } } }}>
          <VerdictBanner verdict={verdict} score={score} />
        </motion.div>

        {verdict === "GO" && (
          <motion.div variants={{ hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } } }}>
            <VibeScore
              score={score}
              breakdown={{
                tech: analysisMap.architect,
                market: analysisMap.scout,
                innovation: analysisMap.catalyst,
                risk: analysisMap.guardian,
                userImpact: analysisMap.advocate,
              }}
            />
          </motion.div>
        )}

        {verdict === "CONDITIONAL" && (
          <motion.div variants={{ hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } } }}>
            <Card className="border-amber-400/20 bg-amber-500/10">
              <CardHeader>
                <CardTitle>Scope Adjustments</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-amber-100">The council recommends a reduced first release scope.</p>
                <ul className="space-y-2 text-sm text-amber-50/90">
                  {suggestions.map((item) => (
                    <li key={item} className="rounded-lg border border-amber-300/20 bg-black/10 px-3 py-2">
                      {item}
                    </li>
                  ))}
                </ul>
                <Button onClick={() => router.push(`/meeting/${params.id}`)}>Retry Meeting</Button>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {verdict === "NO-GO" && (
          <motion.div variants={{ hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } } }}>
            <Card className="border-red-400/20 bg-red-500/10">
              <CardHeader>
                <CardTitle>Failure Reasons & Alternatives</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <ul className="space-y-2 text-sm text-red-50/90">
                  {noGoReasons.map((item) => (
                    <li key={item} className="rounded-lg border border-red-300/20 bg-black/10 px-3 py-2">
                      {item}
                    </li>
                  ))}
                </ul>
                <Button asChild variant="secondary">
                  <Link href="/">Try Another</Link>
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        )}

        <motion.div variants={{ hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } } }}>
        <Tabs defaultValue="documents" className="space-y-4">
          <TabsList className="h-auto flex-wrap justify-start gap-2 bg-muted/20 p-1">
            <TabsTrigger value="documents">Documents</TabsTrigger>
            <TabsTrigger value="code">Code</TabsTrigger>
            <TabsTrigger value="deploy">Deploy</TabsTrigger>
          </TabsList>

          <TabsContent value="documents">
            <DocViewer documents={extractDocuments(result.documents)} />
          </TabsContent>

          <TabsContent value="code">
            <CodePreview files={extractCodeFiles(result.code_files)} />
          </TabsContent>

          <TabsContent value="deploy">
            <DeployStatus
              currentStep={
                result.deployment?.status === "local_running" ? "live"
                : result.deployment?.status === "github_only" ? "push"
                : result.deployment?.liveUrl ? "live"
                : result.deployment?.status?.startsWith("deployment_error") ? "failed"
                : "deploy"
              }
              repoUrl={result.deployment?.repoUrl}
              liveUrl={result.deployment?.liveUrl}
              error={result.deployment?.status?.startsWith("deployment_error") ? result.deployment.status : undefined}
              status={result.deployment?.status}
              ciStatus={result.deployment?.ciStatus}
              ciUrl={result.deployment?.ciUrl}
              localUrl={result.deployment?.localUrl}
              localBackendUrl={result.deployment?.localBackendUrl}
              localFrontendUrl={result.deployment?.localFrontendUrl}
            />
          </TabsContent>
        </Tabs>
        </motion.div>
      </motion.div>
    </div>
  );
}

function LoadingState({ meetingId }: { meetingId: string }) {
  return (
    <div className="min-h-screen px-4 py-10">
      <div className="mx-auto w-full max-w-[1440px] space-y-5">
        <div className="space-y-2">
          <Skeleton className="h-10 w-80" />
          <Skeleton className="h-4 w-56" />
          <p className="text-xs text-muted-foreground">Session: {meetingId}</p>
        </div>
        <Skeleton className="h-36 w-full" />
        <Skeleton className="h-[28rem] w-full" />
      </div>
    </div>
  );
}

function VerdictBanner({ verdict, score }: { verdict: Verdict; score: number }) {
  const animatedScore = useAnimatedCounter(score);

  const glowMap: Record<Verdict, string> = {
    GO: "shadow-[0_0_30px_rgba(16,185,129,0.2)]",
    CONDITIONAL: "shadow-[0_0_30px_rgba(245,158,11,0.2)]",
    "NO-GO": "shadow-[0_0_30px_rgba(239,68,68,0.2)]",
  };

  const config: Record<Verdict, { border: string; bg: string; title: string; text: string; color: string }> = {
    GO: { border: "border-emerald-400/25", bg: "bg-emerald-500/10", title: "GO — Build Approved", text: "The council approves full execution and deployment.", color: "text-emerald-100" },
    CONDITIONAL: { border: "border-amber-400/25", bg: "bg-amber-500/10", title: "CONDITIONAL — Proceed with Scope Reduction", text: "Move forward after tightening MVP boundaries.", color: "text-amber-100" },
    "NO-GO": { border: "border-red-400/25", bg: "bg-red-500/10", title: "NO-GO — Pivot Recommended", text: "Core risks currently outweigh launch readiness.", color: "text-red-100" },
  };

  const c = config[verdict];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" as const }}
    >
      <Card className={`${c.border} ${c.bg} ${glowMap[verdict]}`}>
        <CardHeader>
          <CardTitle>{c.title}</CardTitle>
        </CardHeader>
        <CardContent className={`text-sm ${c.color}`}>
          Vibe Score <span className="font-bold tabular-nums">{animatedScore}</span>. {c.text}
        </CardContent>
      </Card>
    </motion.div>
  );
}

function normalizeVerdict(value: string | undefined): Verdict {
  if (value === "GO") return "GO";
  if (value === "CONDITIONAL") return "CONDITIONAL";
  return "NO-GO";
}

function extractAnalysisMap(analyses: Record<string, unknown>[]) {
  const map = {
    architect: 0,
    scout: 0,
    guardian: 0,
    catalyst: 0,
    advocate: 0,
  };

  analyses.forEach((entry) => {
    const agent = typeof entry.agent === "string" ? entry.agent.toLowerCase() : "";
    const score = typeof entry.score === "number" ? entry.score : 0;
    if (agent.includes("architect")) map.architect = score;
    if (agent.includes("scout")) map.scout = score;
    if (agent.includes("guardian")) map.guardian = score;
    if (agent.includes("catalyst")) map.catalyst = score;
    if (agent.includes("advocate")) map.advocate = score;
  });

  return map;
}

function extractDocuments(input: Record<string, unknown>[]) {
  const result = input
    .map((doc) => {
      const type = typeof doc.type === "string" ? doc.type : "prd";
      const title = typeof doc.title === "string" ? doc.title : "Untitled";
      const content = typeof doc.content === "string" ? doc.content : "";

      if (
        type !== "prd" &&
        type !== "tech-spec" &&
        type !== "api-spec" &&
        type !== "db-schema" &&
        type !== "app-spec"
      ) {
        return null;
      }

      return { type, title, content };
    })
    .filter((value): value is { type: "prd" | "tech-spec" | "api-spec" | "db-schema" | "app-spec"; title: string; content: string } => value !== null);

  return result;
}

function extractCodeFiles(codeFiles?: Array<{ path: string; content: string; language: string; source: string }>): Array<{ path: string; content: string; language: string }> {
  if (!codeFiles || codeFiles.length === 0) return [];
  return codeFiles.map(f => ({ path: f.path, content: f.content, language: f.language }));
}
