"use client";

import { useSession, signOut } from "next-auth/react";
import { ShieldAlert, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function PendingPage() {
  const { data: session } = useSession();

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex size-12 items-center justify-center rounded-full bg-destructive/10">
            <ShieldAlert className="size-6 text-destructive" />
          </div>
          <CardTitle className="text-xl font-bold">
            Access Restricted
          </CardTitle>
          <CardDescription className="text-sm leading-relaxed">
            Due to significant cost increases from LLM API and DigitalOcean
            infrastructure usage, access to this platform is currently restricted
            to authorized users only.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border border-border bg-muted/50 p-4 text-center text-sm">
            <p className="text-muted-foreground">
              To request access, please contact
            </p>
            <a
              href="mailto:sejun@2weeks.co"
              className="mt-1 inline-block font-medium text-primary hover:underline"
            >
              sejun@2weeks.co
            </a>
          </div>
          {session?.user?.email && (
            <p className="text-center text-xs text-muted-foreground">
              Signed in as{" "}
              <span className="font-medium text-foreground">
                {session.user.email}
              </span>
            </p>
          )}
        </CardContent>
        <CardFooter>
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
