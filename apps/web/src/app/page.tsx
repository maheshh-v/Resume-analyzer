"use client";

import {
  ArrowRight,
  CheckCircle2,
  FileSearch,
  Fingerprint,
  GitBranch,
  Lock,
  MessageSquareText,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/auth-context";

const PIPELINE = [
  {
    icon: FileSearch,
    step: "01",
    title: "Extract every claim",
    body: "The resume is parsed into discrete, verifiable claims — each one cited back to the exact sentence it came from. No paraphrasing, no invented detail.",
  },
  {
    icon: GitBranch,
    step: "02",
    title: "Cross-check the evidence",
    body: "Claims are checked against public signals — GitHub, package registries, papers, patents — while consistency checks catch impossible timelines and overlaps.",
  },
  {
    icon: MessageSquareText,
    step: "03",
    title: "Interview what's still unproven",
    body: "For claims evidence can't settle, the AI generates adaptive questions grounded in the candidate's own experience. Vague answers get probed, not passed.",
  },
  {
    icon: ScrollText,
    step: "04",
    title: "Deliver a cited verdict",
    body: "A hiring summary where every verdict links to its evidence. No score, no ranking, no automated reject — a human makes the call, fully informed.",
  },
];

const DIFFERENTIATORS = [
  {
    icon: Fingerprint,
    title: "Evidence it can't fake",
    body: "The citation guardrail is enforced in code: a source is only accepted if the URL resolves and the quote is a literal substring of it. The model physically cannot cite something that isn't there.",
  },
  {
    icon: Lock,
    title: "A tamper-evident record",
    body: "Every step — extraction, evidence, interview, decision — lands in a hash-chained Evidence Ledger. Months later, you can prove exactly how a call was reached.",
  },
  {
    icon: Users,
    title: "Inbound that verifies itself",
    body: "Share one public apply link. Candidates apply with their own resume and verification starts the instant they submit — zero data entry, every applicant pre-checked.",
  },
  {
    icon: ShieldCheck,
    title: "Human-in-the-loop by design",
    body: "No scores. No rankings. No automated pass/fail. The system surfaces cited evidence; a person decides — auditable, defensible, and bias-conscious.",
  },
];

const STATS = [
  { value: "98.4%", label: "Claim-extraction F1", note: "resumes → clean, citable claims" },
  { value: "100%", label: "Citation validity", note: "every cited span is real" },
  { value: "0", label: "Planted lies passed as verified", note: "on the fabrication-safety set" },
];

export default function RootPage() {
  const { session, loading } = useAuth();
  const router = useRouter();

  // Render the landing immediately (no spinner flash); an authenticated visitor is bounced
  // to their workspace by this effect once the session hydrates.
  useEffect(() => {
    if (!loading && session) router.replace("/jobs");
  }, [loading, session, router]);

  return (
    <div className="ambient min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/70 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card">
              <ShieldCheck className="size-4.5" aria-hidden />
            </span>
            <span className="text-lg font-semibold tracking-tight">Recruit</span>
            <span className="mt-0.5 hidden text-xs text-muted-foreground sm:inline">evidence-first hiring</span>
          </div>
          <nav className="flex items-center gap-1.5">
            <Link href="/benchmarks" className={buttonVariants({ variant: "ghost", size: "sm", className: "hidden sm:inline-flex" })}>
              Benchmarks
            </Link>
            <ThemeToggle />
            <Link href="/login" className={buttonVariants({ size: "sm" })}>
              Sign in
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="fade-up space-y-7">
          <Badge variant="outline" className="gap-1.5 py-1 pr-3 pl-2">
            <Sparkles className="size-3.5 text-primary" aria-hidden />
            AI-powered evidence verification
          </Badge>
          <h1 className="text-4xl leading-[1.1] font-semibold tracking-tight text-balance sm:text-5xl">
            Anyone can generate a perfect resume.{" "}
            <span className="text-primary">Verify what candidates can actually defend.</span>
          </h1>
          <p className="max-w-xl text-lg leading-relaxed text-muted-foreground">
            Recruit reads a resume, cites every claim back to its source, cross-checks the evidence, and interviews
            what&apos;s still unproven — then hands a human a decision they can defend months later.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Link href="/login" className={buttonVariants({ size: "lg" })}>
              Start verifying
              <ArrowRight className="size-4" aria-hidden />
            </Link>
            <Link href="/benchmarks" className={buttonVariants({ variant: "outline", size: "lg" })}>
              See the accuracy numbers
            </Link>
          </div>
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="size-4 text-verdict-verified" aria-hidden />
            No scores. No black-box ranking. Every verdict cited; every decision human.
          </p>
        </div>

        {/* Product glimpse — a mock evidence card, no screenshot needed */}
        <div className="fade-up relative" style={{ animationDelay: "120ms" }}>
          <div className="absolute -inset-4 -z-10 rounded-3xl bg-primary/[0.06] blur-2xl" aria-hidden />
          <div className="space-y-3 rounded-2xl bg-card p-5 shadow-lift ring-1 ring-foreground/[0.07]">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Evidence summary</span>
              <Badge variant="secondary" className="gap-1 text-xs">
                <Fingerprint className="size-3" aria-hidden />
                ledger #4213
              </Badge>
            </div>
            <EvidenceRow
              verdict="verified"
              claim="5 years of Kubernetes, incl. multi-cluster at scale"
              note="github.com/…/k8s-operator — 3 yrs of commits, cited"
            />
            <EvidenceRow
              verdict="partial"
              claim="Led the ML platform team"
              note="Corroborated by title; scope unconfirmed — flagged for interview"
            />
            <EvidenceRow
              verdict="contradicted"
              claim="Full-time role 2021–2023"
              note="Overlaps a full-time MS in the same window"
            />
            <div className="flex items-center gap-2 border-t border-border/60 pt-3 text-xs text-muted-foreground">
              <ShieldCheck className="size-3.5 text-primary" aria-hidden />
              Each line links to its evidence. A recruiter decides — the system never does.
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-border/60 bg-muted/30">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
          <div className="max-w-2xl space-y-3">
            <span className="text-sm font-semibold text-primary">How it works</span>
            <h2 className="text-3xl font-semibold tracking-tight">A verification pipeline, not a keyword match</h2>
            <p className="text-base leading-relaxed text-muted-foreground">
              Four stages turn a PDF into a defensible hiring decision. Every stage is offline-testable and leaves an
              auditable trace.
            </p>
          </div>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {PIPELINE.map(({ icon: Icon, step, title, body }, i) => (
              <div
                key={title}
                className="fade-up relative flex flex-col gap-3 rounded-xl bg-card p-5 shadow-card ring-1 ring-foreground/[0.07]"
                style={{ animationDelay: `${i * 70}ms` }}
              >
                <div className="flex items-center justify-between">
                  <span className="flex size-9 items-center justify-center rounded-lg bg-primary/[0.08] text-primary ring-1 ring-primary/10">
                    <Icon className="size-4.5" aria-hidden />
                  </span>
                  <span className="font-mono text-xs text-muted-foreground/60">{step}</span>
                </div>
                <p className="font-medium">{title}</p>
                <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Differentiators */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
        <div className="max-w-2xl space-y-3">
          <span className="text-sm font-semibold text-primary">Why it&apos;s trusted</span>
          <h2 className="text-3xl font-semibold tracking-tight">Built so the evidence can&apos;t be faked</h2>
          <p className="text-base leading-relaxed text-muted-foreground">
            The hard guarantees live in code, not in a prompt — which is exactly what makes the output defensible.
          </p>
        </div>
        <div className="mt-10 grid gap-5 sm:grid-cols-2">
          {DIFFERENTIATORS.map(({ icon: Icon, title, body }, i) => (
            <div
              key={title}
              className="fade-up flex gap-4 rounded-xl bg-card p-6 shadow-card ring-1 ring-foreground/[0.07]"
              style={{ animationDelay: `${i * 70}ms` }}
            >
              <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/[0.08] text-primary ring-1 ring-primary/10">
                <Icon className="size-5" aria-hidden />
              </span>
              <div className="space-y-1.5">
                <p className="font-medium">{title}</p>
                <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Accuracy band */}
      <section className="border-y border-border/60 bg-muted/30">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="max-w-xl space-y-3">
              <span className="text-sm font-semibold text-primary">Measured, not claimed</span>
              <h2 className="text-3xl font-semibold tracking-tight">Accuracy you can reproduce</h2>
              <p className="text-base leading-relaxed text-muted-foreground">
                Scored against a hand-labelled dataset of real resumes, planted lies, and messy edge cases. The number
                that matters most: how often a fabrication slips through as verified.
              </p>
            </div>
            <Link href="/benchmarks" className={buttonVariants({ variant: "outline" })}>
              Full methodology
              <ArrowRight className="size-4" aria-hidden />
            </Link>
          </div>
          <div className="mt-10 grid gap-5 sm:grid-cols-3">
            {STATS.map(({ value, label, note }, i) => (
              <div
                key={label}
                className="fade-up rounded-xl bg-card p-6 shadow-card ring-1 ring-foreground/[0.07]"
                style={{ animationDelay: `${i * 70}ms` }}
              >
                <p className="font-mono text-4xl font-semibold tabular-nums text-primary">{value}</p>
                <p className="mt-2 font-medium">{label}</p>
                <p className="text-sm text-muted-foreground">{note}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <div className="brand-panel relative overflow-hidden rounded-3xl px-8 py-14 text-center text-white sm:px-16">
          <div className="brand-grid absolute inset-0" aria-hidden />
          <div className="relative mx-auto max-w-2xl space-y-6">
            <h2 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
              Stop reading resumes. Start verifying them.
            </h2>
            <p className="text-lg leading-relaxed text-white/70">
              Paste a job description, drop in resumes or share an apply link, and let the evidence pipeline do the
              first pass — so your team spends its time on the candidates who hold up.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Link href="/login" className={buttonVariants({ variant: "secondary", size: "lg" })}>
                Get started
                <ArrowRight className="size-4" aria-hidden />
              </Link>
              <Link
                href="/benchmarks"
                className={buttonVariants({
                  variant: "outline",
                  size: "lg",
                  className: "border-white/25 bg-transparent text-white hover:bg-white/10 hover:text-white",
                })}
              >
                See the benchmarks
              </Link>
            </div>
          </div>
        </div>
      </section>

      <footer className="mx-auto max-w-6xl px-4 pb-12 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-border/60 pt-6 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <span className="flex size-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <ShieldCheck className="size-3.5" aria-hidden />
            </span>
            <span>Recruit — evidence-first hiring verification</span>
          </div>
          <div className="flex items-center gap-5">
            <Link href="/benchmarks" className="transition-colors hover:text-foreground">
              Benchmarks
            </Link>
            <Link href="/login" className="transition-colors hover:text-foreground">
              Sign in
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

const VERDICT_STYLES = {
  verified: { dot: "bg-verdict-verified", label: "Verified", labelClass: "text-verdict-verified" },
  partial: { dot: "bg-verdict-partial", label: "Partial", labelClass: "text-verdict-partial" },
  contradicted: { dot: "bg-verdict-contradicted", label: "Contradicted", labelClass: "text-verdict-contradicted" },
} as const;

function EvidenceRow({
  verdict,
  claim,
  note,
}: {
  verdict: keyof typeof VERDICT_STYLES;
  claim: string;
  note: string;
}) {
  const style = VERDICT_STYLES[verdict];
  return (
    <div className="rounded-lg bg-muted/40 p-3">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium">{claim}</span>
        <span className={`inline-flex shrink-0 items-center gap-1.5 text-xs font-medium ${style.labelClass}`}>
          <span className={`size-1.5 rounded-full ${style.dot}`} aria-hidden />
          {style.label}
        </span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{note}</p>
    </div>
  );
}
