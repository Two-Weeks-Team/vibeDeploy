"use client";

import { SessionProvider } from "next-auth/react";

export function AuthSessionProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  return <SessionProvider basePath="/auth/api" refetchInterval={300}>{children}</SessionProvider>;
}
