"use client";

import { motion } from "framer-motion";
import { Github, Rocket, Calendar } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { DeployedApp } from "@/types/dashboard";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

const VERDICT_COLORS = {
  GO: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  CONDITIONAL: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  "NO-GO": "bg-red-500/10 text-red-500 border-red-500/20",
};

export function DeployedApps({ deployments }: { deployments: DeployedApp[] }) {
  if (!deployments || deployments.length === 0) {
    return (
      <motion.div
        variants={fadeUp}
        initial="hidden"
        animate="show"
        className="flex flex-col items-center justify-center py-24 text-center"
      >
        <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
          <Rocket className="h-8 w-8 text-primary" />
        </div>
        <h3 className="text-xl font-semibold mb-2">No deployed apps yet</h3>
        <p className="text-muted-foreground max-w-md">
          Start an evaluation to generate and deploy an app. Once deployed, it will appear here.
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      {deployments.map((app) => {
        const title =
          app.idea_summary?.slice(0, 60) ||
          app.input_prompt?.slice(0, 60) ||
          app.thread_id;

        return (
          <motion.div key={app.thread_id} variants={fadeUp}>
            <Card className="h-full flex flex-col border-border/50 bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
              <CardHeader className="pb-4">
                <div className="flex justify-between items-start gap-4 mb-2">
                  <Badge
                    variant="outline"
                    className={cn("font-mono font-bold", VERDICT_COLORS[app.verdict])}
                  >
                    {app.verdict}
                  </Badge>
                  <div className="text-2xl font-bold font-mono tracking-tighter">
                    {app.score.toFixed(1)}
                  </div>
                </div>
                <CardTitle className="text-lg leading-tight line-clamp-2" title={title}>
                  {title}
                  {(app.idea_summary?.length > 60 || app.input_prompt?.length > 60) && "..."}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col justify-end gap-4">
                <div className="flex items-center text-xs text-muted-foreground">
                  <Calendar className="mr-1.5 h-3.5 w-3.5" />
                  {new Date(app.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Button
                    variant="default"
                    className="w-full bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20"
                    asChild
                  >
                    <a href={app.deployment.liveUrl} target="_blank" rel="noopener noreferrer">
                      <Rocket className="mr-2 h-4 w-4" />
                      Live App
                    </a>
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full border-border/50 hover:bg-muted/50"
                    asChild
                  >
                    <a href={app.deployment.repoUrl} target="_blank" rel="noopener noreferrer">
                      <Github className="mr-2 h-4 w-4" />
                      GitHub
                    </a>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        );
      })}
    </motion.div>
  );
}