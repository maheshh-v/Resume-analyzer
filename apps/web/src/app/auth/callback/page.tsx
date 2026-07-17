"use client";

import { Loader2, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { InlineError } from "@/components/states";
import { createClient } from "@/lib/supabase/client";
import { safeRedirectPath } from "@/lib/utils";

function friendlyAuthError(message: string): string {
  if (/code verifier|pkce/i.test(message)) {
    return "This sign-in link was started in a different browser or has expired. Please sign in again — it will work this time.";
  }
  if (/expired|invalid/i.test(message)) {
    return "This sign-in link has expired or was already used. Please sign in again.";
  }
  return message;
}

function Callback() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const next = safeRedirectPath(searchParams.get("next"));
    const code = searchParams.get("code");
    const errDesc = searchParams.get("error_description");
    const supabase = createClient();
    let cancelled = false;

    async function completeSignIn() {
      // The browser client auto-detects ?code= on creation and exchanges it itself,
      // consuming the one-shot PKCE verifier. getSession() waits for that to settle, so
      // if it already succeeded we must NOT exchange again — the second attempt would
      // fail with "code verifier not found" even though the user is signed in.
      const { data: first } = await supabase.auth.getSession();
      if (cancelled) return;
      if (first.session) {
        router.replace(next);
        router.refresh();
        return;
      }

      if (errDesc) {
        setError(friendlyAuthError(errDesc));
        return;
      }
      if (!code) {
        router.replace("/login");
        return;
      }

      const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
      if (cancelled) return;
      if (exchangeError) {
        const { data: raced } = await supabase.auth.getSession();
        if (cancelled) return;
        if (raced.session) {
          router.replace(next);
          router.refresh();
          return;
        }
        setError(friendlyAuthError(exchangeError.message));
        return;
      }
      router.replace(next);
      router.refresh();
    }

    void completeSignIn();
    return () => {
      cancelled = true;
    };
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
