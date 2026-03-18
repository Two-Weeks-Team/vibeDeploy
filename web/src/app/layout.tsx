import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ErrorBoundary } from "@/components/shared";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "vibeDeploy — Zero prompts. Zero coding. One button deploys a live app.",
  description:
    "AI discovers ideas from YouTube, validates with academic research, writes type-safe code, and ships to DigitalOcean — autonomously.",
  openGraph: {
    title: "vibeDeploy",
    description: "Zero-Prompt AI deployment — from YouTube trend to live app, fully autonomous",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "vibeDeploy",
    description: "Zero-Prompt AI deployment — from YouTube trend to live app, fully autonomous",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        <ErrorBoundary>{children}</ErrorBoundary>
      </body>
    </html>
  );
}
