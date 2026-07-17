"use client";

import { FileSearch, Link2, Loader2, MessageSquareText, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { InlineError } from "@/components/states";
import { ThemeToggle } from "@/components/theme-toggle";
import { API_BASE } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { safeRedirectPath } from "@/lib/utils";

const VALUE_PROPS = [
  {
    icon: FileSearch,
    title: "Claims, not keywords",
    body: "Every technical claim is extracted from the resume and cited back to the exact sentence it came from.",
  },
  {
    icon: MessageSquareText,
    title: "Interviews ChatGPT can't sit",
    body: "Adaptive questions grounded in the candidate's own claimed experience — vague answers get probed, not passed.",
  },
  {
    icon: Link2,
    title: "A tamper-evident record",
    body: "Every step lands in a hash-chained Evidence Ledger. You can prove how a decision was reached, months later.",
  },
];

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" aria-hidden>
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 1.46 14.97.5 12 .5A11 11 0 0 0 2.18 7.06L5.84 9.9c.87-2.6 3.3-4.53 6.16-4.53Z"
      />
    </svg>
  );
}

/** Which action is in flight. Deliberately NOT cleared on success: the spinner must keep
 * spinning until the router actually swaps the page (or the browser leaves for Google) —
 * clearing it on the auth response alone leaves a dead, feedback-less gap. */
type PendingAction = "google" | "password" | null;

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<"sign-in" | "sign-up">("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingAction>(null);

  const next = safeRedirectPath(searchParams.get("next"));
  const busy = pending !== null;

  // Free-tier API hosts sleep after inactivity and take ~30-50s to wake. Ping while the
  // user is still typing so their first real request lands on a warm server.
  useEffect(() => {
    void fetch(`${API_BASE}/health`).catch(() => {});
  }, []);

  async function handleGoogle() {
    setError(null);
    setNotice(null);
    setPending("google");
    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}` },
    });
    if (authError) {
      setPending(null);
      setError(authError.message);
    }
    // On success the browser navigates to Google — keep the spinner until it does.
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setPending("password");
    const supabase = createClient();

    if (mode === "sign-up") {
      const { data, error: authError } = await supabase.auth.signUp({ email, password });
      if (authError) {
        setPending(null);
        setError(authError.message);
        return;
      }
      // If email confirmation is enabled in Supabase, no session is returned yet.
      if (!data.session) {
        setPending(null);
        setNotice("Account created — check your inbox for a confirmation link, then sign in.");
        setMode("sign-in");
        return;
      }
      router.push(next);
      router.refresh();
      return;
    }

    const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
    if (authError) {
      setPending(null);
      setError(authError.message);
      return;
    }
    // Keep `pending` set: the button stays disabled with its spinner until /jobs mounts.
    router.push(next);
    router.refresh();
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      {/* Brand panel */}
      <div className="brand-panel relative hidden flex-col justify-between overflow-hidden p-12 text-white lg:flex">
        <div className="brand-grid absolute inset-0" aria-hidden />
        <div className="relative flex items-center gap-2.5">
          <span className="flex size-9 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/20 backdrop-blur">
            <ShieldCheck className="size-5" aria-hidden />
          </span>
          <span className="text-xl font-semibold tracking-tight">Recruit</span>
        </div>

        <div className="relative max-w-lg space-y-10">
          <h1 className="text-[2rem] leading-[1.2] font-semibold tracking-tight text-balance">
            Anyone can generate a perfect resume.{" "}
            <span className="text-white/70">Verify what candidates can actually defend.</span>
          </h1>
          <ul className="space-y-6">
            {VALUE_PROPS.map(({ icon: Icon, title, body }, i) => (
              <li key={title} className="fade-up flex gap-4" style={{ animationDelay: `${150 + i * 120}ms` }}>
                <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-white/[0.08] ring-1 ring-white/15">
                  <Icon className="size-4.5" aria-hidden />
                </span>
                <div className="space-y-1">
                  <p className="font-medium">{title}</p>
                  <p className="text-sm leading-relaxed text-white/60">{body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs tracking-wide text-white/45">
          No scores. No rankings. Every verdict cited; every decision human.
        </p>
      </div>

      {/* Form panel */}
      <div className="relative flex items-center justify-center p-6">
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>
        <div className="fade-up w-full max-w-sm space-y-7">
          <div className="space-y-1 lg:hidden">
            <div className="flex items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card">
                <ShieldCheck className="size-4.5" aria-hidden />
              </span>
              <span className="text-lg font-semibold tracking-tight">Recruit</span>
            </div>
            <p className="text-sm text-muted-foreground">Evidence-first hiring verification.</p>
          </div>

          <div className="space-y-1.5">
            <h2 className="text-[1.6rem] font-semibold tracking-tight">
              {mode === "sign-in" ? "Welcome back" : "Create your account"}
            </h2>
            <p className="text-sm text-muted-foreground">
              {mode === "sign-in" ? "Sign in to your recruiter workspace." : "Set up a recruiter workspace in seconds."}
            </p>
          </div>

          {notice && (
            <Alert>
              <AlertDescription>{notice}</AlertDescription>
            </Alert>
          )}

          <Button
            type="button"
            variant="outline"
            size="lg"
            className="w-full"
            onClick={handleGoogle}
            disabled={busy}
          >
            {pending === "google" ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <GoogleIcon />}
            {pending === "google" ? "Redirecting to Google..." : "Continue with Google"}
          </Button>

          <div className="flex items-center gap-3">
            <span className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">or continue with email</span>
            <span className="h-px flex-1 bg-border" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                placeholder="you@company.com"
                disabled={busy}
                className="h-10"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === "sign-in" ? "current-password" : "new-password"}
                disabled={busy}
                className="h-10"
              />
            </div>
            {error && <InlineError message={error} />}
            <Button type="submit" size="lg" className="h-10 w-full" disabled={busy}>
              {pending === "password" && <Loader2 className="size-4 animate-spin" aria-hidden />}
              {pending === "password"
                ? mode === "sign-in"
                  ? "Signing you in..."
                  : "Creating your account..."
                : mode === "sign-in"
                  ? "Sign in"
                  : "Sign up"}
            </Button>
          </form>

          <Button
            variant="link"
            className="w-full text-muted-foreground"
            disabled={busy}
            onClick={() => {
              setError(null);
              setMode(mode === "sign-in" ? "sign-up" : "sign-in");
            }}
          >
            {mode === "sign-in" ? "Need an account? Sign up" : "Already have an account? Sign in"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
