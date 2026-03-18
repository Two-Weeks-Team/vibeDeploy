"use client";

import { motion } from "framer-motion";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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
    return <p className="text-sm text-muted-foreground">No code generated yet.</p>;
  }

  return (
    <Tabs defaultValue={files[0].path} className="space-y-4">
      <TabsList className="h-auto w-full flex-wrap justify-start gap-1 bg-muted/20 p-1">
        {files.map((file) => (
          <TabsTrigger key={file.path} value={file.path} className="text-xs">
            {file.path}
          </TabsTrigger>
        ))}
      </TabsList>
      {files.map((file) => (
        <TabsContent key={file.path} value={file.path}>
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <ScrollArea className="h-[28rem] rounded-xl border border-white/10 bg-black/30">
              <SyntaxHighlighter
                language={normalizeLanguage(file.language)}
                style={oneDark}
                customStyle={{
                  margin: 0,
                  minHeight: "28rem",
                  background: "transparent",
                  fontSize: "0.78rem",
                }}
              >
                {file.content}
              </SyntaxHighlighter>
            </ScrollArea>
          </motion.div>
        </TabsContent>
      ))}
    </Tabs>
  );
}

function normalizeLanguage(language: string): string {
  const value = language.toLowerCase();
  if (value === "ts") return "typescript";
  if (value === "js") return "javascript";
  if (value === "py") return "python";
  if (value === "sh") return "bash";
  return value;
}
