"use client";

import { Loader2, LogOut, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";

export default function RecruiterLayout({ children }: { children: ReactNode }) {
  const { session, loading, signOut } = useAuth();
  const router = useRouter();

  // Gate children on a hydrated session: on a hard navigation the Supabase session loads
  // asynchronously, and any query mounted before it exists would fire with a null token,
  // 401, and never refetch (the token isn't part of any query key).
  useEffect(() => {
    if (!loading && !session) router.replace("/login");
  }, [loading, session, router]);

  async function handleSignOut() {
    await signOut();
    router.push("/login");
    router.refresh();
  }

  if (loading || !session) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" aria-hidden />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link href="/jobs" className="flex items-center gap-2">
            <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <ShieldCheck className="size-4" aria-hidden />
            </span>
            <span className="text-lg font-semibold tracking-tight">Recruit</span>
            <span className="mt-0.5 hidden text-xs text-muted-foreground sm:inline">evidence-first hiring</span>
          </Link>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            {session?.user.email && <span className="hidden sm:inline">{session.user.email}</span>}
            <Button variant="outline" size="sm" onClick={handleSignOut}>
              <LogOut className="size-3.5" aria-hidden />
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
      <footer className="mx-auto max-w-6xl px-4 pt-4 pb-8">
        <p className="text-xs text-muted-foreground">
          No scores. No rankings. No automated decisions — every verdict is cited, every decision is human.
        </p>
      </footer>
    </div>
  );
}
