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
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground">
          Skip to main content
        </a>
        <main id="main-content">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </body>
    </html>
  );
}
