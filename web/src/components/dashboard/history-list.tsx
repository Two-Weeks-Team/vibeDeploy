"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { FileText, Code, Rocket, Brain, Target, Clock, Github } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MeetingResultFull, BrainstormResultFull, VerdictType } from "@/types/dashboard";

interface HistoryListProps {
  results: MeetingResultFull[];
  brainstorms: BrainstormResultFull[];
}

type FilterType = "all" | "evaluation" | "brainstorm";
type FilterVerdict = "all" | VerdictType;

type UnifiedItem =
  | { type: "evaluation"; data: MeetingResultFull; date: Date }
  | { type: "brainstorm"; data: BrainstormResultFull; date: Date };

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } },
};

export function HistoryList({ results, brainstorms }: HistoryListProps) {
  const [typeFilter, setTypeFilter] = useState<FilterType>("all");
  const [verdictFilter, setVerdictFilter] = useState<FilterVerdict>("all");
  const [visibleCount, setVisibleCount] = useState(20);
  const [selectedItem, setSelectedItem] = useState<UnifiedItem | null>(null);

  const items = useMemo(() => {
    const unified: UnifiedItem[] = [
      ...results.map((r) => ({ type: "evaluation" as const, data: r, date: new Date(r.created_at) })),
      ...brainstorms.map((b) => ({ type: "brainstorm" as const, data: b, date: new Date(b.created_at) })),
    ];

    return unified
      .sort((a, b) => b.date.getTime() - a.date.getTime())
      .filter((item) => {
        if (typeFilter !== "all" && item.type !== typeFilter) return false;
        if (item.type === "evaluation" && verdictFilter !== "all") {
          if (item.data.verdict !== verdictFilter) return false;
        }
        if (item.type === "brainstorm" && verdictFilter !== "all") return false;
        return true;
      });
  }, [results, brainstorms, typeFilter, verdictFilter]);

  const visibleItems = items.slice(0, visibleCount);

  const getItemTitle = (item: UnifiedItem) =>
    item.type === "evaluation"
      ? item.data.idea_summary || item.data.input_prompt || item.data.thread_id
      : item.data.idea_summary || item.data.thread_id;

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case "GO":
        return <Badge className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20">GO</Badge>;
      case "CONDITIONAL":
        return <Badge className="bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 border-amber-500/20">CONDITIONAL</Badge>;
      case "NO-GO":
        return <Badge className="bg-red-500/10 text-red-500 hover:bg-red-500/20 border-red-500/20">NO-GO</Badge>;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
        <div className="flex flex-wrap gap-2">
          <span className="text-sm text-muted-foreground flex items-center mr-2">Type:</span>
          <Badge
            variant={typeFilter === "all" ? "default" : "outline"}
            className="cursor-pointer"
            onClick={() => setTypeFilter("all")}
          >
            All
          </Badge>
          <Badge
            variant={typeFilter === "evaluation" ? "default" : "outline"}
            className={cn("cursor-pointer", typeFilter === "evaluation" && "bg-blue-500 hover:bg-blue-600")}
            onClick={() => setTypeFilter("evaluation")}
          >
            Evaluation
          </Badge>
          <Badge
            variant={typeFilter === "brainstorm" ? "default" : "outline"}
            className={cn("cursor-pointer", typeFilter === "brainstorm" && "bg-purple-500 hover:bg-purple-600")}
            onClick={() => setTypeFilter("brainstorm")}
          >
            Brainstorm
          </Badge>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="text-sm text-muted-foreground flex items-center mr-2">Verdict:</span>
          <Badge
            variant={verdictFilter === "all" ? "default" : "outline"}
            className="cursor-pointer"
            onClick={() => setVerdictFilter("all")}
          >
            All
          </Badge>
          <Badge
            variant={verdictFilter === "GO" ? "default" : "outline"}
            className={cn("cursor-pointer", verdictFilter === "GO" && "bg-emerald-500 hover:bg-emerald-600")}
            onClick={() => setVerdictFilter("GO")}
          >
            GO
          </Badge>
          <Badge
            variant={verdictFilter === "CONDITIONAL" ? "default" : "outline"}
            className={cn("cursor-pointer", verdictFilter === "CONDITIONAL" && "bg-amber-500 hover:bg-amber-600")}
            onClick={() => setVerdictFilter("CONDITIONAL")}
          >
            CONDITIONAL
          </Badge>
          <Badge
            variant={verdictFilter === "NO-GO" ? "default" : "outline"}
            className={cn("cursor-pointer", verdictFilter === "NO-GO" && "bg-red-500 hover:bg-red-600")}
            onClick={() => setVerdictFilter("NO-GO")}
          >
            NO-GO
          </Badge>
        </div>
      </div>

      {items.length === 0 ? (
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm py-12">
          <div className="flex flex-col items-center justify-center text-muted-foreground">
            <Target className="w-12 h-12 mb-4 opacity-20" />
            <p>No results match your filters</p>
          </div>
        </Card>
      ) : (
        <motion.div variants={containerVariants} initial="hidden" animate="visible" className="space-y-3">
          <AnimatePresence mode="popLayout">
            {visibleItems.map((item) => (
              <motion.div key={item.type === "evaluation" ? item.data.thread_id : item.data.thread_id} variants={fadeUp} layout>
                <Card
                  className="border-border/50 bg-card/50 backdrop-blur-sm hover:bg-accent/50 transition-colors cursor-pointer"
                  onClick={() => setSelectedItem(item)}
                >
                  <CardContent className="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div className="flex min-w-0 items-center gap-4">
                      <div className="flex min-w-0 flex-col">
                        <div className="flex items-center gap-2 mb-1">
                          {item.type === "evaluation" ? (
                            <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">
                              <Target className="w-3 h-3 mr-1" /> Eval
                            </Badge>
                          ) : (
                            <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/20">
                              <Brain className="w-3 h-3 mr-1" /> Brainstorm
                            </Badge>
                          )}
                          <span className="font-mono text-xs text-muted-foreground/70">
                            {item.data.thread_id}
                          </span>
                        </div>
                        <div className="line-clamp-2 text-sm font-medium leading-6 text-foreground">
                          {getItemTitle(item)}
                        </div>
                        <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
                          <Clock className="w-3 h-3" />
                          {item.date.toLocaleString()}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      {item.type === "evaluation" && (
                        <>
                          <div className="text-right">
                            <div className="text-2xl font-bold">{item.data.score.toFixed(1)}</div>
                            <div className="text-xs text-muted-foreground">Score</div>
                          </div>
                          {getVerdictBadge(item.data.verdict)}
                          {item.data.deployment && (
                            <div className="flex items-center gap-2 ml-2 border-l border-border/50 pl-4">
                              <a
                                href={item.data.deployment.repoUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-2 rounded-full hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                                onClick={(e) => e.stopPropagation()}
                                title="View Repository"
                              >
                                <Github className="w-4 h-4" />
                              </a>
                              {item.data.deployment.liveUrl && !item.data.deployment.liveUrl.includes("vibedeploy") ? (
                                <a
                                  href={item.data.deployment.liveUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="p-2 rounded-full hover:bg-accent text-muted-foreground hover:text-primary transition-colors"
                                  onClick={(e) => e.stopPropagation()}
                                  title="View Live App"
                                >
                                  <Rocket className="w-4 h-4" />
                                </a>
                              ) : (
                                <span className="p-2 rounded-full text-muted-foreground/30 cursor-not-allowed" title="Not yet deployed">
                                  <Rocket className="w-4 h-4" />
                                </span>
                              )}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      )}

      {visibleCount < items.length && (
        <div className="flex justify-center pt-4">
          <Button variant="outline" onClick={() => setVisibleCount((prev) => prev + 20)}>
            Load More
          </Button>
        </div>
      )}

      <Dialog open={!!selectedItem} onOpenChange={(open) => !open && setSelectedItem(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="truncate">{selectedItem ? getItemTitle(selectedItem) : ""}</DialogTitle>
            <DialogDescription className="space-y-1">
              <div>{selectedItem?.type === "evaluation" ? "Evaluation" : "Brainstorm"}</div>
              <div className="font-mono text-xs">{selectedItem?.data.thread_id}</div>
              <div>{selectedItem?.date.toLocaleString()}</div>
            </DialogDescription>
          </DialogHeader>

          <ScrollArea className="flex-1 pr-4">
            {selectedItem?.type === "evaluation" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between p-4 rounded-lg bg-accent/50">
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Final Score</div>
                    <div className="text-4xl font-bold">{selectedItem.data.score.toFixed(1)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground mb-1 text-right">Verdict</div>
                    {getVerdictBadge(selectedItem.data.verdict)}
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-4">Agent Scores</h3>
                  <div className="space-y-4">
                    {selectedItem.data.analyses?.map((analysis) => (
                      <div key={analysis.agent} className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="font-medium capitalize">{analysis.agent}</span>
                          <span>{analysis.score}/100</span>
                        </div>
                        <Progress value={analysis.score} className="h-2" />
                      </div>
                    ))}
                  </div>
                </div>

                {selectedItem.data.deployment && (
                  <>
                    <Separator />
                    <div>
                      <h3 className="text-lg font-semibold mb-4">Deployment</h3>
                      <div className="flex gap-4">
                        {selectedItem.data.deployment.liveUrl && !selectedItem.data.deployment.liveUrl.includes("vibedeploy") ? (
                          <Button asChild variant="outline" className="flex-1">
                            <a href={selectedItem.data.deployment.liveUrl} target="_blank" rel="noreferrer">
                              <Rocket className="w-4 h-4 mr-2" /> Live App
                            </a>
                          </Button>
                        ) : (
                          <Button variant="outline" className="flex-1 text-muted-foreground" disabled>
                            <Rocket className="w-4 h-4 mr-2" /> Deploying...
                          </Button>
                        )}
                        <Button asChild variant="outline" className="flex-1">
                          <a href={selectedItem.data.deployment.repoUrl} target="_blank" rel="noreferrer">
                            <Code className="w-4 h-4 mr-2" /> Repository
                          </a>
                        </Button>
                      </div>
                    </div>
                  </>
                )}

                {selectedItem.data.documents && selectedItem.data.documents.length > 0 && (
                  <>
                    <Separator />
                    <div>
                      <h3 className="text-lg font-semibold mb-4">Generated Documents</h3>
                      <div className="grid grid-cols-2 gap-2">
                        {selectedItem.data.documents.map((doc) => (
                          <div key={doc.type} className="flex items-center gap-2 p-2 rounded border border-border/50 bg-card/50">
                            <FileText className="w-4 h-4 text-blue-400" />
                            <span className="text-sm font-medium">{doc.type}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {selectedItem?.type === "brainstorm" && (
              <div className="space-y-6">
                <div className="p-4 rounded-lg bg-accent/50">
                  <h3 className="text-lg font-semibold mb-2">Idea Summary</h3>
                  <p className="text-sm text-muted-foreground">{selectedItem.data.idea_summary}</p>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-4">Top Ideas</h3>
                  <div className="space-y-3">
                    {selectedItem.data.synthesis?.top_ideas?.map((idea) => (
                      <Card key={idea.title} className="border-border/50 bg-card/50">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-medium">{idea.title}</h4>
                            <Badge variant="outline" className="capitalize">{idea.source_agent}</Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">{idea.description}</p>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-4">Recommended Direction</h3>
                  <p className="text-sm text-muted-foreground">{selectedItem.data.synthesis?.recommended_direction}</p>
                </div>
              </div>
            )}
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </div>
  );
}
