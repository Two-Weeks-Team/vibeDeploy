"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Play, X, ExternalLink, Clapperboard, BookOpen, TrendingUp, Zap, Trash2 } from "lucide-react";
import type { ZPCard } from "@/types/zero-prompt";

const SCORE_CRITERIA = [
  { label: "Proposal Clarity", weightKey: "proposal_clarity_weight", signalKey: "proposal_clarity_signal", pointsKey: "proposal_clarity_points", detail: "How concrete the app name, core feature, audience, stack, and screens are" },
  { label: "Execution", weightKey: "execution_feasibility_weight", signalKey: "execution_feasibility_signal", pointsKey: "execution_feasibility_points", detail: "Whether the MVP scope looks buildable in the proposed timeframe" },
  { label: "Market", weightKey: "market_viability_weight", signalKey: "market_viability_signal", pointsKey: "market_viability_points", detail: "How viable the proposed MVP looks after competition and audience checks" },
  { label: "Differentiation", weightKey: "mvp_differentiation_weight", signalKey: "mvp_differentiation_signal", pointsKey: "mvp_differentiation_points", detail: "How distinct the MVP wedge is, not just how interesting the source video was" },
  { label: "Evidence", weightKey: "evidence_strength_weight", signalKey: "evidence_strength_signal", pointsKey: "evidence_strength_points", detail: "How much supporting evidence exists from MVP-aligned research, technical grounding, and novelty" },
] as const;

function humanizeReasonCode(reasonCode?: string): string {
  if (!reasonCode) return "";
  return reasonCode.replace(/_/g, " ");
}

function getLowScoreSignals(card: ZPCard): string[] {
  const signals: string[] = [];
  const breakdown = card.score_breakdown;

  if ((breakdown?.proposal_clarity_signal ?? 100) < 60) {
    signals.push("The MVP proposal itself is still too vague — naming, core feature, audience, or screens need to be more concrete.");
  }
  if ((breakdown?.execution_feasibility_signal ?? 100) < 60) {
    signals.push("The proposed MVP scope looks too broad or not execution-ready enough for a fast build.");
  }
  if ((breakdown?.market_viability_signal ?? 100) < 55) {
    signals.push("Even with the MVP framing, the market still looks crowded or demand is not strong enough yet.");
  }
  if ((breakdown?.mvp_differentiation_signal ?? 100) < 55) {
    signals.push("The MVP wedge is still too generic — it needs a sharper user promise or a clearer competitive edge.");
  }
  if ((breakdown?.evidence_strength_signal ?? 100) < 50) {
    signals.push("The MVP does not yet have enough supporting evidence from research quality, technical grounding, or novelty signals.");
  }
  if ((breakdown?.originality_signal ?? 100) < (breakdown?.originality_threshold ?? 55)) {
    signals.push("The MVP still feels too commodity-like — similar idea lists, directories, or stale patterns already exist in the market.");
  }

  if (card.reason) {
    signals.push(card.reason);
  }
  if (card.reason_code === "market_saturated") {
    signals.push(`Competition is crowded${card.saturation ? ` (${card.saturation} saturation)` : ""}, so market opportunity scored poorly.`);
  }
  if (card.reason_code === "weak_differentiation") {
    signals.push("The idea did not show enough unique features or defensible gaps versus existing competitors.");
  }
  if (card.reason_code === "weak_paper_backing") {
    signals.push("The paper-backed novelty boost stayed too small, so the concept looked under-validated.");
  }
  if (card.reason_code === "low_confidence") {
    signals.push("The combined MVP clarity, execution, market, and evidence signals were not strong enough to clear the GO threshold.");
  }
  if ((card.papers_found ?? 0) <= 1) {
    signals.push(`Only ${card.papers_found ?? 0} relevant papers were found, which weakens the novelty portion of the score.`);
  }
  if ((card.novelty_boost ?? 0) < 0.05) {
    signals.push(`Novelty boost is only +${((card.novelty_boost ?? 0) * 100).toFixed(0)}%, which contributes very little to the final score.`);
  }
  if (card.competitors_found && Number(card.competitors_found) >= 5) {
    signals.push(`${card.competitors_found} competitors were found, which increases saturation pressure and hurts market/differentiation.`);
  }

  return Array.from(new Set(signals)).slice(0, 4);
}

function formatSignal(value?: number): string {
  if (typeof value !== "number") return "n/a";
  return `${value.toFixed(1)} / 100`;
}

interface CardDetailModalProps {
  card: ZPCard | null;
  isOpen: boolean;
  onClose: () => void;
  onQueueBuild: (cardId: string) => void;
  onPassCard: (cardId: string) => void;
  onDeleteCard?: (cardId: string) => void;
}

export function CardDetailModal({ card, isOpen, onClose, onQueueBuild, onPassCard, onDeleteCard }: CardDetailModalProps) {
  if (!card) return null;

  const isRealVideo = card.video_id && !card.video_id.startsWith("fallback-");
  const youtubeUrl = isRealVideo ? `https://youtube.com/watch?v=${card.video_id}` : null;
  const insightKeyCounts = new Map<string, number>();
  const keyedInsights = (card.insights ?? []).map((insight) => {
    const count = (insightKeyCounts.get(insight) ?? 0) + 1;
    insightKeyCounts.set(insight, count);
    return { insight, key: `${card.card_id}-insight-${count}-${insight.slice(0, 20)}` };
  });
  const keyPageCounts = new Map<string, number>();
  const keyedPages = (card.mvp_proposal?.key_pages ?? []).map((page) => {
    const count = (keyPageCounts.get(page) ?? 0) + 1;
    keyPageCounts.set(page, count);
    return { page, key: `${card.card_id}-page-${count}-${page}` };
  });
  const lowScoreSignals = getLowScoreSignals(card);
  const hasExactBreakdown = SCORE_CRITERIA.every((item) => typeof card.score_breakdown?.[item.pointsKey] === "number");

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[550px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex justify-between items-start mb-2">
            <Badge variant={card.score >= 70 ? "default" : "destructive"}>
              {card.status.replace("_", " ").toUpperCase()}
            </Badge>
            <Badge variant="outline" className="bg-background text-xs">
              {card.card_id.slice(0, 8)}
            </Badge>
          </div>
          <DialogTitle className="text-xl leading-tight">{card.title || card.video_id}</DialogTitle>
          <DialogDescription>
            {card.domain ? `Domain: ${card.domain}` : "Analysis details"}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          <div className="flex items-center gap-4">
            <div>
              <p className="text-xs text-muted-foreground mb-1">Vibe Score</p>
              <span className={`text-3xl font-bold ${card.score >= 70 ? "text-emerald-500" : card.score >= 50 ? "text-amber-500" : "text-red-500"}`}>
                {card.score}
              </span>
              <span className="text-sm text-muted-foreground ml-1">/ 100</span>
            </div>
            {card.reason_code && (
              <Badge variant="outline" className="ml-auto">{card.reason_code.replace(/_/g, " ")}</Badge>
            )}
          </div>

          {card.reason && (
            <div className="bg-muted/30 p-3 rounded-lg border border-border/50">
              <p className="text-sm">{card.reason}</p>
            </div>
          )}

          <div className="space-y-2 rounded-lg border border-border/50 bg-background/70 p-3">
            <div className="flex items-center justify-between gap-3">
              <h4 className="text-sm font-semibold">Score criteria</h4>
              <span className="text-xs text-muted-foreground">GO if score is 70+</span>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {SCORE_CRITERIA.map((item) => (
                <div key={item.label} className="rounded-md border border-border/40 bg-muted/20 p-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium">{item.label}</span>
                    <Badge variant="outline" className="text-[10px]">{card.score_breakdown?.[item.weightKey] ?? 0}%</Badge>
                  </div>
                  <p className="mt-1 text-[11px] text-muted-foreground">{item.detail}</p>
                  {hasExactBreakdown ? (
                    <div className="mt-2 space-y-1 text-[11px] text-muted-foreground">
                      <div className="flex items-center justify-between gap-2">
                        <span>Signal</span>
                        <span className="font-medium text-foreground/80">{formatSignal(card.score_breakdown?.[item.signalKey])}</span>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <span>Contribution</span>
                        <span className="font-medium text-foreground/80">{card.score_breakdown?.[item.pointsKey]?.toFixed(1)} pts</span>
                      </div>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground">
              Final score = weighted sum of the five contributions above. The backend marks cards as GO at 70+.
            </p>
          </div>

          {typeof card.score_breakdown?.originality_signal === "number" && (
            <div className="space-y-2 rounded-lg border border-border/50 bg-background/70 p-3">
              <div className="flex items-center justify-between gap-3">
                <h4 className="text-sm font-semibold">Originality gate</h4>
                <Badge variant={card.score_breakdown.originality_signal >= (card.score_breakdown.originality_threshold ?? 55) ? "default" : "destructive"}>
                  {card.score_breakdown.originality_signal.toFixed(0)} / 100
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Blocks stale idea-list, directory, and generic “AI tools / business ideas” products even when the generated MVP copy looks polished.
              </p>
            </div>
          )}

          {card.score < 70 && lowScoreSignals.length > 0 && (
            <div className="space-y-2 rounded-lg border border-red-500/20 bg-red-500/5 p-3">
              <div className="flex items-center justify-between gap-3">
                <h4 className="text-sm font-semibold text-red-500">Why this score is low</h4>
                {card.reason_code ? (
                  <Badge variant="outline" className="text-xs text-red-500">
                    {humanizeReasonCode(card.reason_code)}
                  </Badge>
                ) : null}
              </div>
              <ul className="space-y-1.5">
                {lowScoreSignals.map((signal) => (
                  <li key={`${card.card_id}-${signal}`} className="text-sm text-muted-foreground">
                    - {signal}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            {card.domain && (
              <div className="flex items-center gap-2 text-sm">
                <Zap className="w-4 h-4 text-blue-500" />
                <span className="text-muted-foreground">Domain:</span>
                <span className="font-medium">{card.domain}</span>
              </div>
            )}
            {card.papers_found !== undefined && (
              <div className="flex items-center gap-2 text-sm">
                <BookOpen className="w-4 h-4 text-purple-500" />
                <span className="text-muted-foreground">Papers:</span>
                <span className="font-medium">{card.papers_found}</span>
              </div>
            )}
            {card.competitors_found && (
              <div className="flex items-center gap-2 text-sm">
                <TrendingUp className="w-4 h-4 text-orange-500" />
                <span className="text-muted-foreground">Competitors:</span>
                <span className="font-medium">{card.competitors_found}</span>
              </div>
            )}
            {card.saturation && (
              <div className="flex items-center gap-2 text-sm">
                <TrendingUp className="w-4 h-4 text-orange-500" />
                <span className="text-muted-foreground">Saturation:</span>
                <Badge variant="outline" className="text-xs">{card.saturation}</Badge>
              </div>
            )}
            {card.novelty_boost !== undefined && card.novelty_boost > 0 && (
              <div className="flex items-center gap-2 text-sm col-span-2">
                <Zap className="w-4 h-4 text-yellow-500" />
                <span className="text-muted-foreground">Novelty boost:</span>
                <span className="font-medium text-yellow-600">+{(card.novelty_boost * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>

          {youtubeUrl && (
            <a href={youtubeUrl} target="_blank" rel="noopener noreferrer"
               className="flex items-center gap-2 text-sm text-red-500 hover:underline">
              <Clapperboard className="w-4 h-4" />
              Watch source video
            </a>
          )}

          {card.video_summary && (
            <div className="space-y-1.5">
              <h4 className="text-sm font-semibold flex items-center gap-1.5">
                <Clapperboard className="w-4 h-4 text-red-400" />
                Video Summary
              </h4>
              <p className="text-sm text-muted-foreground leading-relaxed bg-muted/20 p-3 rounded-lg">
                {card.video_summary}
              </p>
            </div>
          )}

          {card.insights && card.insights.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="text-sm font-semibold flex items-center gap-1.5">
                <Zap className="w-4 h-4 text-yellow-400" />
                Key Insights
              </h4>
              <ul className="space-y-1">
                {keyedInsights.map(({ insight, key }) => (
                  <li key={key} className="text-sm text-muted-foreground flex items-start gap-2">
                    <span className="text-yellow-500 mt-0.5">•</span>
                    <span>{insight}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {card.mvp_proposal && card.mvp_proposal.app_name && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold flex items-center gap-1.5">
                <Play className="w-4 h-4 text-emerald-400" />
                MVP Proposal
              </h4>
              <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-emerald-400">{card.mvp_proposal.app_name}</span>
                  {card.mvp_proposal.estimated_days && (
                    <Badge variant="outline" className="text-xs">{card.mvp_proposal.estimated_days} days est.</Badge>
                  )}
                </div>
                {card.mvp_proposal.core_feature && (
                  <p className="text-sm text-muted-foreground">{card.mvp_proposal.core_feature}</p>
                )}
                {card.mvp_proposal.tech_stack && (
                  <p className="text-xs text-muted-foreground/70">Tech: {card.mvp_proposal.tech_stack}</p>
                )}
                {card.mvp_proposal.key_pages && card.mvp_proposal.key_pages.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {keyedPages.map(({ page, key }) => (
                      <Badge key={key} variant="secondary" className="text-xs">{page}</Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 mt-2">
          {card.status === "go_ready" && (
            <>
              <Button data-modal-pass-card-id={card.card_id} variant="outline" onClick={() => { onPassCard(card.card_id); onClose(); }}>
                <X className="w-4 h-4 mr-2" /> Skip
              </Button>
              <Button data-modal-go-card-id={card.card_id} className="bg-emerald-600 hover:bg-emerald-700 text-white"
                onClick={() => { onQueueBuild(card.card_id); onClose(); }}>
                <Play className="w-4 h-4 mr-2" /> Build App
              </Button>
            </>
          )}
          {card.status === "deployed" && (
            <div className="flex gap-2 w-full">
              {card.live_url && (
                <Button asChild className="flex-1 bg-emerald-600 hover:bg-emerald-700">
                  <a href={card.live_url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="w-4 h-4 mr-2" /> View App
                  </a>
                </Button>
              )}
              {card.repo_url && (
                <Button asChild variant="outline" className="flex-1">
                  <a href={card.repo_url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="w-4 h-4 mr-2" /> GitHub
                  </a>
                </Button>
              )}
            </div>
          )}
          {(card.status === "nogo" || card.status === "passed" || card.status === "build_failed") && onDeleteCard && (
            <Button
              variant="destructive"
              onClick={() => {
                onDeleteCard(card.card_id);
                onClose();
              }}
            >
              <Trash2 className="w-4 h-4 mr-2" /> Delete
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
