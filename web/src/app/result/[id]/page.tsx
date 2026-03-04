"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
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
      <div className="mx-auto w-full max-w-[1440px] space-y-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Council Result Dashboard</h1>
          <p className="text-sm text-muted-foreground md:text-base">Session {params.id}</p>
        </div>

        <VerdictBanner verdict={verdict} score={score} />

        {verdict === "GO" && (
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
        )}

        {verdict === "CONDITIONAL" && (
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
        )}

        {verdict === "NO-GO" && (
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
        )}

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
            <CodePreview files={extractCodeFiles(result.documents)} />
          </TabsContent>

          <TabsContent value="deploy">
            <DeployStatus
              currentStep={result.deployment?.liveUrl ? "live" : "deploy"}
              repoUrl={result.deployment?.repoUrl}
              liveUrl={result.deployment?.liveUrl}
            />
          </TabsContent>
        </Tabs>
      </div>
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
  if (verdict === "GO") {
    return (
      <Card className="border-emerald-400/25 bg-emerald-500/10">
        <CardHeader>
          <CardTitle>GO — Build Approved</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-emerald-100">Vibe Score {score}. The council approves full execution and deployment.</CardContent>
      </Card>
    );
  }

  if (verdict === "CONDITIONAL") {
    return (
      <Card className="border-amber-400/25 bg-amber-500/10">
        <CardHeader>
          <CardTitle>CONDITIONAL — Proceed with Scope Reduction</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-amber-100">Vibe Score {score}. Move forward after tightening MVP boundaries.</CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-red-400/25 bg-red-500/10">
      <CardHeader>
        <CardTitle>NO-GO — Pivot Recommended</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-red-100">Vibe Score {score}. Core risks currently outweigh launch readiness.</CardContent>
    </Card>
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
        type !== "db-schema"
      ) {
        return null;
      }

      return { type, title, content };
    })
    .filter((value): value is { type: "prd" | "tech-spec" | "api-spec" | "db-schema"; title: string; content: string } => value !== null);

  return result;
}

function extractCodeFiles(input: Record<string, unknown>[]) {
  return input
    .map((doc) => {
      const path = typeof doc.path === "string" ? doc.path : null;
      const content = typeof doc.code === "string" ? doc.code : typeof doc.content === "string" ? doc.content : null;
      const language = typeof doc.language === "string" ? doc.language : "typescript";

      if (!path || !content) return null;

      return { path, content, language };
    })
    .filter((value): value is { path: string; content: string; language: string } => value !== null);
}
