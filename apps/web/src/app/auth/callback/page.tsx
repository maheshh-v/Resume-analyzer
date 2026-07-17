"use client";

import { Loader2, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { InlineError } from "@/components/states";
import { createClient } from "@/lib/supabase/client";

function Callback() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const next = searchParams.get("next") ?? "/jobs";
    const code = searchParams.get("code");
    const errDesc = searchParams.get("error_description");

    if (errDesc) {
      setError(errDesc);
      return;
    }
    if (!code) {
      // No code and no error — nothing to exchange; send them home.
      router.replace("/login");
      return;
    }

    const supabase = createClient();
    supabase.auth.exchangeCodeForSession(code).then(({ error: exchangeError }) => {
      if (exchangeError) {
        setError(exchangeError.message);
        return;
      }
      router.replace(next);
      router.refresh();
    });
  }, [router, searchParams]);

  if (error) {
    return (
      <div className="ambient flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
        <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-card">
          <ShieldCheck className="size-5" aria-hidden />
        </span>
        <InlineError message={`Sign-in failed: ${error}`} />
        <a href="/login" className="text-sm font-medium text-primary underline-offset-4 hover:underline">
          Back to sign in
        </a>
      </div>
    );
  }

  return (
    <div className="ambient flex min-h-screen flex-col items-center justify-center gap-4">
      <span className="fade-up flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-card">
        <ShieldCheck className="size-5" aria-hidden />
      </span>
      <div className="fade-up flex items-center gap-2 text-sm text-muted-foreground" style={{ animationDelay: "80ms" }}>
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Signing you in securely...
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense>
      <Callback />
    </Suspense>
  );
}
