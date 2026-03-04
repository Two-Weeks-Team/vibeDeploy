"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

/**
 * DocViewer — Displays generated documents (PRD, Tech Spec, API Spec, DB Schema).
 * Uses tabs to switch between document types. Renders markdown content.
 * TODO (Wave 7): Markdown rendering, copy-to-clipboard, download as PDF.
 */

interface DocViewerProps {
  documents: {
    type: "prd" | "tech-spec" | "api-spec" | "db-schema";
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
    <Tabs defaultValue={documents[0].type}>
      <TabsList>
        {documents.map((doc) => (
          <TabsTrigger key={doc.type} value={doc.type}>
            {doc.title}
          </TabsTrigger>
        ))}
      </TabsList>
      {documents.map((doc) => (
        <TabsContent key={doc.type} value={doc.type}>
          <pre className="whitespace-pre-wrap rounded-lg bg-muted p-4 text-sm">
            {doc.content}
          </pre>
        </TabsContent>
      ))}
    </Tabs>
  );
}
