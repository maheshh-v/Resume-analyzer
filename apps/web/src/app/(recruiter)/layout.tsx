"use client";

import { Loader2, LogOut, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/auth-context";

export default function RecruiterLayout({ children }: { children: ReactNode }) {
  const { session, loading, signOut } = useAuth();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  // Gate children on a hydrated session: on a hard navigation the Supabase session loads
  // asynchronously, and any query mounted before it exists would fire with a null token,
  // 401, and never refetch (the token isn't part of any query key).
  useEffect(() => {
    if (!loading && !session) router.replace("/login");
  }, [loading, session, router]);

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await signOut();
      router.push("/login");
      router.refresh();
    } catch {
      setSigningOut(false);
    }
  }

  if (loading || !session) {
    return (
      <div className="ambient flex min-h-screen flex-col items-center justify-center gap-4">
        <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-card">
          <ShieldCheck className="size-5" aria-hidden />
        </span>
        <Loader2 className="size-5 animate-spin text-muted-foreground" aria-hidden />
      </div>
    );
  }

  return (
    <div className="ambient min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border/70 bg-background/75 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <Link href="/jobs" className="group flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card transition-transform duration-300 group-hover:scale-105">
              <ShieldCheck className="size-4.5" aria-hidden />
            </span>
            <span className="text-lg font-semibold tracking-tight">Recruit</span>
            <span className="mt-0.5 hidden text-xs text-muted-foreground sm:inline">evidence-first hiring</span>
          </Link>
          <div className="flex items-center gap-1.5">
            {session?.user.email && (
              <span className="mr-1 hidden max-w-[16rem] truncate text-sm text-muted-foreground sm:inline">
                {session.user.email}
              </span>
            )}
            <ThemeToggle />
            <Button variant="outline" size="sm" onClick={handleSignOut} disabled={signingOut}>
              {signingOut ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden />
              ) : (
                <LogOut className="size-3.5" aria-hidden />
              )}
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">{children}</main>
      <footer className="mx-auto max-w-6xl px-4 pt-4 pb-10 sm:px-6">
        <p className="text-xs leading-relaxed text-muted-foreground/80">
          No scores. No rankings. No automated decisions — every verdict is cited, every decision is human.
        </p>
      </footer>
    </div>
  );
}
