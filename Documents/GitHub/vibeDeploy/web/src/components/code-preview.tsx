"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

/**
 * CodePreview — Shows generated code (frontend + backend) with syntax highlighting.
 * File tree on the left, code on the right.
 * TODO (Wave 7): Syntax highlighting, file tree, download as zip.
 */

interface CodeFile {
  path: string;
  content: string;
  language: string;
}

interface CodePreviewProps {
  files: CodeFile[];
}

export function CodePreview({ files }: CodePreviewProps) {
  if (files.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No code generated yet.
      </p>
    );
  }

  return (
    <Tabs defaultValue={files[0].path}>
      <TabsList className="flex-wrap">
        {files.map((file) => (
          <TabsTrigger key={file.path} value={file.path} className="text-xs">
            {file.path}
          </TabsTrigger>
        ))}
      </TabsList>
      {files.map((file) => (
        <TabsContent key={file.path} value={file.path}>
          <pre className="overflow-x-auto whitespace-pre rounded-lg bg-muted p-4 text-xs">
            <code>{file.content}</code>
          </pre>
        </TabsContent>
      ))}
    </Tabs>
  );
}
