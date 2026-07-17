"use client";

import { Loader2, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";

export default function RootPage() {
  const { session, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(session ? "/jobs" : "/login");
  }, [loading, session, router]);

  return (
    <div className="ambient flex min-h-screen flex-col items-center justify-center gap-4">
      <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-card">
        <ShieldCheck className="size-5" aria-hidden />
      </span>
      <Loader2 className="size-5 animate-spin text-muted-foreground" aria-hidden />
    </div>
  );
}
