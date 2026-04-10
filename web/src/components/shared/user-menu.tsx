"use client";

import { useState, useRef, useEffect } from "react";
import { useSession, signOut } from "next-auth/react";
import { LogOut } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function UserMenu() {
  const { data: session, status } = useSession();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  if (status === "loading") {
    return (
      <div className="size-8 animate-pulse rounded-full bg-muted" />
    );
  }

  if (status === "unauthenticated" || !session?.user) {
    return null;
  }

  const { user } = session;
  const initials = (user.name ?? user.email ?? "?")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center gap-2 rounded-full p-0.5 transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-expanded={open}
        aria-haspopup="true"
        aria-label="User menu"
      >
        <Avatar size="default">
          {user.image && <AvatarImage src={user.image} alt={user.name ?? ""} />}
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-2 w-64 rounded-lg border border-border bg-popover p-3 shadow-lg"
        >
          <div className="mb-3 space-y-1">
            {user.name && (
              <p className="text-sm font-medium text-foreground">{user.name}</p>
            )}
            {user.email && (
              <p className="text-xs text-muted-foreground">{user.email}</p>
            )}
            {user.domain && (
              <Badge variant="secondary" className="mt-1.5 text-xs">
                {user.domain}
              </Badge>
            )}
          </div>
          <div className="border-t border-border pt-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
              onClick={() => signOut({ callbackUrl: "/auth/signin" })}
              role="menuitem"
            >
              <LogOut className="size-4" />
              Sign out
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
