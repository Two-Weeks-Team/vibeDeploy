"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Play, X, ExternalLink, Youtube, BookOpen, TrendingUp, Zap } from "lucide-react";
import type { ZPCard } from "@/types/zero-prompt";

interface CardDetailModalProps {
  card: ZPCard | null;
  isOpen: boolean;
  onClose: () => void;
  onQueueBuild: (cardId: string) => void;
  onPassCard: (cardId: string) => void;
}

export function CardDetailModal({ card, isOpen, onClose, onQueueBuild, onPassCard }: CardDetailModalProps) {
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
              <Youtube className="w-4 h-4" />
              Watch source video
            </a>
          )}

          {card.video_summary && (
            <div className="space-y-1.5">
              <h4 className="text-sm font-semibold flex items-center gap-1.5">
                <Youtube className="w-4 h-4 text-red-400" />
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
                <X className="w-4 h-4 mr-2" /> Pass
              </Button>
              <Button data-modal-go-card-id={card.card_id} className="bg-emerald-600 hover:bg-emerald-700 text-white"
                onClick={() => { onQueueBuild(card.card_id); onClose(); }}>
                <Play className="w-4 h-4 mr-2" /> GO! Build
              </Button>
            </>
          )}
          {card.status === "deployed" && card.thread_id && (
            <Button asChild className="w-full sm:w-auto">
              <a href={`/result/${card.thread_id}`}>
                <ExternalLink className="w-4 h-4 mr-2" /> View Result
              </a>
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
