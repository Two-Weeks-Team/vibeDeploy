"use client";

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";

interface DocViewerProps {
  documents: {
    type: "prd" | "tech-spec" | "api-spec" | "db-schema" | "app-spec";
    title: string;
    content: string;
  }[];
}

export function DocViewer({ documents }: DocViewerProps) {
  if (documents.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No documents generated yet.
      </p>
    );
  }

  return (
    <Tabs defaultValue={documents[0].type} className="space-y-4">
      <TabsList className="h-auto w-full flex-wrap justify-start gap-2 bg-muted/20 p-1">
        {documents.map((doc) => (
          <TabsTrigger key={doc.type} value={doc.type} className="text-xs">
            {doc.title}
          </TabsTrigger>
        ))}
      </TabsList>
      {documents.map((doc) => (
        <TabsContent key={doc.type} value={doc.type}>
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <ScrollArea className="h-[28rem] rounded-xl border border-white/10 bg-card/60 p-5">
              <article className="prose prose-invert max-w-none prose-headings:tracking-tight prose-p:text-sm prose-li:text-sm">
                <ReactMarkdown>{doc.content}</ReactMarkdown>
              </article>
            </ScrollArea>
          </motion.div>
        </TabsContent>
      ))}
    </Tabs>
  );
}
