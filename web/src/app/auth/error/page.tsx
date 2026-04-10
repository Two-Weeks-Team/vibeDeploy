"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { AlertTriangle, LogOut } from "lucide-react";
import { signOut } from "next-auth/react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const errorMessages: Record<string, string> = {
  Configuration: "There is a problem with the server configuration.",
  AccessDenied: "You do not have permission to sign in.",
  Verification: "The verification link has expired or has already been used.",
  Default: "An unexpected authentication error occurred.",
};

function ErrorContent() {
  const searchParams = useSearchParams();
  const errorType = searchParams.get("error") || "Default";
  const message = errorMessages[errorType] || errorMessages.Default;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex size-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="size-6 text-destructive" />
          </div>
          <CardTitle className="text-xl font-bold">
            Authentication Error
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-sm text-muted-foreground">
            {message}
          </p>
        </CardContent>
        <CardFooter className="flex flex-col gap-2">
          <Button
            variant="default"
            className="w-full"
            onClick={() => (window.location.href = "/auth/signin")}
          >
            Try again
          </Button>
          <Button
            variant="outline"
            className="w-full gap-2"
            onClick={() => signOut({ callbackUrl: "/auth/signin" })}
          >
            <LogOut className="size-4" />
            Sign out
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}

export default function AuthErrorPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      }
    >
      <ErrorContent />
    </Suspense>
  );
}
