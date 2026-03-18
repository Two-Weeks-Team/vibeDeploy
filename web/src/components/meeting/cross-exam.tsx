"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

interface DebateExchange {
  from: string;
  to: string;
  argument: string;
  response?: string;
}

interface CrossExamProps {
  exchanges: DebateExchange[];
}

export function CrossExam({ exchanges }: CrossExamProps) {
  return (
    <Card className="border-white/10 bg-card/60">
      <CardHeader>
        <CardTitle>Cross-Examination</CardTitle>
      </CardHeader>
      <CardContent>
        {exchanges.length === 0 ? (
          <p className="text-sm text-muted-foreground">Debate has not started yet.</p>
        ) : (
          <ScrollArea className="h-72 pr-3">
            <div className="space-y-3">
              {exchanges.map((ex) => (
                <motion.div
                  key={`${ex.from}-${ex.to}-${ex.argument}-${ex.response ?? ""}`}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className="space-y-1"
                >
                  <div className="inline-flex max-w-[90%] rounded-2xl rounded-bl-sm border border-blue-400/25 bg-blue-500/10 px-3 py-2 text-xs text-blue-100">
                    <span className="font-medium">{ex.from}</span>
                    <span className="mx-1 text-blue-300">to {ex.to}:</span>
                    <span className="text-blue-50/90">{ex.argument}</span>
                  </div>
                  {ex.response && (
                    <div className="ml-auto inline-flex max-w-[90%] rounded-2xl rounded-br-sm border border-rose-400/25 bg-rose-500/10 px-3 py-2 text-xs text-rose-100">
                      <span className="font-medium">{ex.to}</span>
                      <span className="mx-1 text-rose-300">response:</span>
                      <span className="text-rose-50/90">{ex.response}</span>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
