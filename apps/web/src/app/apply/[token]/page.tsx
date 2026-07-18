"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { CheckCircle2, FileText, Loader2, SendHorizonal, ShieldCheck, Unlink } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { InlineError } from "@/components/states";
import { ThemeToggle } from "@/components/theme-toggle";
import { ApiError, publicApplyApi } from "@/lib/api-client";
import { friendlyError } from "@/lib/errors";

/** Public application page — reached via a tokenized link the recruiter shared, exactly like
 * the interview portal. No account, no login: the unguessable token scopes everything. */

function ApplyShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="ambient flex min-h-screen flex-col bg-background">
      <header className="border-b border-border/70 bg-background/75 backdrop-blur-md">
        <div className="mx-auto flex max-w-2xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card">
              <ShieldCheck className="size-4" aria-hidden />
            </span>
            <span className="font-semibold tracking-tight">Recruit</span>
            <span className="text-xs text-muted-foreground">· Apply</span>
          </div>
          <ThemeToggle />
        </div>
      </header>
      <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-10">{children}</main>
      <footer className="mx-auto w-full max-w-2xl px-6 pb-8">
        <p className="text-xs leading-relaxed text-muted-foreground/80">
          The claims on your resume are checked against public evidence (like your GitHub), and every check is recorded
          in an audit ledger the recruiter can&apos;t edit. A human makes every decision — there is no automated
          pass/fail.
        </p>
      </footer>
    </div>
  );
}

export default function PublicApplyPage() {
  const { token } = useParams<{ token: string }>();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [githubLogin, setGithubLogin] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const jobQuery = useQuery({
    queryKey: ["apply", token],
    queryFn: () => publicApplyApi.getJob(token),
    retry: false,
  });

  const submit = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Choose a resume PDF first");
      return publicApplyApi.submitApplication(token, {
        name,
        email,
        github_login: githubLogin || undefined,
        linkedin_url: linkedinUrl || undefined,
        file,
      });
    },
  });

  if (jobQuery.isLoading) {
    return (
      <ApplyShell>
        <div className="space-y-4">
          <Skeleton className="h-8 w-2/3 rounded-md" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      </ApplyShell>
    );
  }

  if (jobQuery.isError) {
    const err = jobQuery.error;
    const message =
      err instanceof ApiError && err.status === 404
        ? "This application link is no longer active. Reach out to the recruiter for a fresh one."
        : friendlyError(err, "Something went wrong loading this job.");
    return (
      <ApplyShell>
        <Card className="fade-up">
          <CardContent className="flex flex-col items-center gap-4 py-14 text-center">
            <span className="flex size-12 items-center justify-center rounded-2xl bg-muted">
              <Unlink className="size-5 text-muted-foreground" aria-hidden />
            </span>
            <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">{message}</p>
          </CardContent>
        </Card>
      </ApplyShell>
    );
  }

  const job = jobQuery.data!;

  if (submit.isSuccess) {
    return (
      <ApplyShell>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, ease: "easeOut" }}>
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
              <motion.span
                initial={{ scale: 0.6, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.15, type: "spring", stiffness: 260, damping: 18 }}
                className="flex size-14 items-center justify-center rounded-full bg-verdict-verified-bg"
              >
                <CheckCircle2 className="size-7 text-verdict-verified" aria-hidden />
              </motion.span>
              <p className="text-lg font-semibold tracking-tight">Application received.</p>
              <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
                Your resume goes straight into evidence verification, and the recruiting team will take it from there.
                If they&apos;d like to dig deeper you&apos;ll get a follow-up link by email.
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </ApplyShell>
    );
  }

  return (
    <ApplyShell>
      <div className="mb-6 space-y-2 fade-up">
        <h1 className="text-2xl font-semibold tracking-tight">{job.job_title}</h1>
        <p className="line-clamp-6 text-sm leading-relaxed whitespace-pre-wrap text-muted-foreground">{job.jd_preview}</p>
      </div>
      <Card className="fade-up" style={{ animationDelay: "80ms" }}>
        <CardContent className="py-6">
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              submit.mutate();
            }}
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="apply-name">Full name</Label>
                <Input id="apply-name" required value={name} onChange={(e) => setName(e.target.value)} disabled={submit.isPending} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="apply-email">Email</Label>
                <Input
                  id="apply-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={submit.isPending}
                />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="apply-github">GitHub username (optional)</Label>
                <Input
                  id="apply-github"
                  value={githubLogin}
                  onChange={(e) => setGithubLogin(e.target.value)}
                  placeholder="Strengthens your application with real evidence"
                  disabled={submit.isPending}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="apply-linkedin">LinkedIn URL (optional)</Label>
                <Input
                  id="apply-linkedin"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  disabled={submit.isPending}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Resume (PDF)</Label>
              <label
                className={
                  "flex cursor-pointer items-center gap-2.5 rounded-xl border border-dashed border-border bg-card/50 px-4 py-3.5 transition-colors hover:border-primary/50" +
                  (submit.isPending ? " pointer-events-none opacity-60" : "")
                }
              >
                <FileText className="size-4 shrink-0 text-primary/70" aria-hidden />
                <span className="min-w-0 truncate text-sm">{file ? file.name : "Choose your resume — PDF, up to 10MB"}</span>
                <input
                  type="file"
                  accept="application/pdf"
                  className="hidden"
                  disabled={submit.isPending}
                  onChange={(e) => {
                    setFile(e.target.files?.[0] ?? null);
                    e.target.value = "";
                  }}
                />
              </label>
            </div>
            {submit.isError && (
              <InlineError message={friendlyError(submit.error, "Couldn't submit your application. Please try again.")} />
            )}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-muted-foreground">Specific, honest resumes do best here — claims get verified.</p>
              <Button type="submit" disabled={submit.isPending || !name.trim() || !email.trim() || !file}>
                {submit.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <SendHorizonal className="size-4" aria-hidden />}
                {submit.isPending ? "Submitting..." : "Submit application"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </ApplyShell>
  );
}
