"use client";

import { FileSearch, Link2, MessageSquareText, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createClient } from "@/lib/supabase/client";

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

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<"sign-in" | "sign-up">("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const next = searchParams.get("next") ?? "/jobs";

  async function handleGoogle() {
    setError(null);
    setNotice(null);
    setLoading(true);
    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}` },
    });
    if (authError) {
      setLoading(false);
      setError(authError.message);
    }
    // On success the browser navigates to Google; no further action here.
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setLoading(true);
    const supabase = createClient();

    if (mode === "sign-up") {
      const { data, error: authError } = await supabase.auth.signUp({ email, password });
      setLoading(false);
      if (authError) {
        setError(authError.message);
        return;
      }
      // If email confirmation is enabled in Supabase, no session is returned yet.
      if (!data.session) {
        setNotice("Account created. Check your email to confirm, then sign in. (Or disable email confirmation in Supabase to sign in instantly.)");
        setMode("sign-in");
        return;
      }
      router.push(next);
      router.refresh();
      return;
    }

    const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (authError) {
      setError(authError.message);
      return;
    }
    router.push(next);
    router.refresh();
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel */}
      <div className="hidden flex-col justify-between bg-primary p-10 text-primary-foreground lg:flex">
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary-foreground/15">
            <ShieldCheck className="size-5" aria-hidden />
          </span>
          <span className="text-xl font-semibold tracking-tight">Recruit</span>
        </div>
        <div className="space-y-8">
          <h1 className="max-w-md text-3xl leading-tight font-semibold tracking-tight">
            Anyone can generate a perfect resume. Verify what candidates can actually defend.
          </h1>
          <ul className="max-w-md space-y-5">
            {VALUE_PROPS.map(({ icon: Icon, title, body }) => (
              <li key={title} className="flex gap-3">
                <Icon className="mt-0.5 size-5 shrink-0 opacity-80" aria-hidden />
                <div>
                  <p className="font-medium">{title}</p>
                  <p className="text-sm opacity-75">{body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs opacity-60">No scores. No rankings. Every verdict cited; every decision human.</p>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm space-y-6">
          <div className="space-y-1 lg:hidden">
            <div className="flex items-center gap-2">
              <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <ShieldCheck className="size-4" aria-hidden />
              </span>
              <span className="text-lg font-semibold tracking-tight">Recruit</span>
            </div>
            <p className="text-sm text-muted-foreground">Evidence-first hiring verification.</p>
          </div>
          <div className="space-y-1">
            <h2 className="text-2xl font-semibold tracking-tight">
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

          <Button type="button" variant="outline" className="w-full" onClick={handleGoogle} disabled={loading}>
            <GoogleIcon />
            Continue with Google
          </Button>

          <div className="flex items-center gap-3">
            <span className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">or</span>
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
              />
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Please wait..." : mode === "sign-in" ? "Sign in" : "Sign up"}
            </Button>
          </form>
          <Button
            variant="link"
            className="w-full text-muted-foreground"
            onClick={() => setMode(mode === "sign-in" ? "sign-up" : "sign-in")}
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
