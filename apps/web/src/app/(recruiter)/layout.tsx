"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";

export default function RecruiterLayout({ children }: { children: ReactNode }) {
  const { session, signOut } = useAuth();
  const router = useRouter();

  async function handleSignOut() {
    await signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="min-h-screen bg-muted/20">
      <header className="border-b bg-background">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link href="/jobs" className="text-lg font-semibold">
            Recruit
          </Link>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            {session?.user.email && <span>{session.user.email}</span>}
            <Button variant="outline" size="sm" onClick={handleSignOut}>
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}
