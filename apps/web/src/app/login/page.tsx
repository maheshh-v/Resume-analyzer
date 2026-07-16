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

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<"sign-in" | "sign-up">("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const supabase = createClient();

    const { error: authError } =
      mode === "sign-in"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password });

    setLoading(false);
    if (authError) {
      setError(authError.message);
      return;
    }

    const next = searchParams.get("next") ?? "/jobs";
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
