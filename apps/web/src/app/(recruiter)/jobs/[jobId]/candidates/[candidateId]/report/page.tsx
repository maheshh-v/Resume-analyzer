"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, CheckCircle2, ExternalLink, Flag, Loader2, Pause, ThumbsDown, ThumbsUp } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { LedgerPanel } from "@/components/ledger-panel";
import { ErrorState, InlineError } from "@/components/states";
import { ImportanceBadge, SpecificityBadge, VerdictBadge } from "@/components/verdict-badge";
import { useApi } from "@/hooks/use-api";
import { friendlyError } from "@/lib/errors";
import { cn } from "@/lib/utils";

const DECISION_OPTIONS = [
  { verdict: "advance", label: "Advance", icon: ThumbsUp, variant: "default" as const },
  { verdict: "hold", label: "Hold", icon: Pause, variant: "secondary" as const },
  { verdict: "decline", label: "Decline", icon: ThumbsDown, variant: "destructive" as const },
];

export default function HiringSummaryPage() {
  const { jobId, candidateId } = useParams<{ jobId: string; candidateId: string }>();
  const api = useApi();
  const [rationale, setRationale] = useState("");
  const [recordedVerdict, setRecordedVerdict] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"report" | "ledger">("report");
  const [pendingVerdict, setPendingVerdict] = useState<string | null>(null);

  const reportQuery = useQuery({ queryKey: ["report", candidateId], queryFn: () => api.getReport(candidateId) });

  const recordDecision = useMutation({
    mutationFn: (verdict: string) => api.recordDecision(candidateId, { verdict, rationale }),
    onSuccess: (decision) => setRecordedVerdict(decision.verdict),
    onSettled: () => setPendingVerdict(null),
  });

  if (reportQuery.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-32 rounded-md" />
        <Skeleton className="h-9 w-1/2 rounded-md" />
        <Skeleton className="h-28 rounded-xl" />
        <Skeleton className="h-72 rounded-xl" />
      </div>
    );
  }
  if (reportQuery.isError || !reportQuery.data) {
    return (
      <ErrorState
        title="Couldn't load the report"
        message={friendlyError(reportQuery.error)}
        onRetry={() => reportQuery.refetch()}
        retrying={reportQuery.isRefetching}
      />
    );
  }

  const report = reportQuery.data;
  const coveragePct =
    report.evidence_coverage_total === 0 ? 0 : (report.evidence_coverage_count / report.evidence_coverage_total) * 100;

  return (
    <div className="space-y-6">
      <div className="fade-up">
        <Link
          href={`/jobs/${jobId}/candidates/${candidateId}`}
          className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" aria-hidden />
          Back to candidate
        </Link>
        <h1 className="text-[1.75rem] font-semibold tracking-tight">Hiring summary</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Every verdict below is cited. Nothing here is a score, ranking, or recommendation.
        </p>
      </div>

      <div
        role="tablist"
        aria-label="Report views"
        className="fade-up inline-flex w-fit items-center gap-1 rounded-lg bg-muted p-1"
        style={{ animationDelay: "60ms" }}
      >
        {(
          [
            { id: "report", label: "Report" },
            { id: "ledger", label: "Evidence Ledger" },
          ] as const
        ).map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            aria-selected={activeTab === id}
            onClick={() => setActiveTab(id)}
            className={cn(
              "rounded-md px-3.5 py-1.5 text-sm font-medium transition-all duration-200",
              activeTab === id ? "bg-background shadow-card" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "report" && (
        <div className="space-y-6">
          <Card className="fade-up" style={{ animationDelay: "100ms" }}>
            <CardContent className="space-y-3 py-4">
              <div className="flex items-baseline gap-3">
                <span className="tabular text-3xl font-semibold tracking-tight">
                  {report.evidence_coverage_count}
                  <span className="text-base font-normal text-muted-foreground"> of {report.evidence_coverage_total}</span>
                </span>
                <span className="text-sm text-muted-foreground">requirements have supporting evidence</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-primary/80 to-primary transition-all duration-700 ease-out"
                  style={{ width: `${coveragePct}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground">{report.evidence_coverage_note}</p>
            </CardContent>
          </Card>

          {report.conflicts.length > 0 && (
            <Card className="fade-up border-verdict-contradicted/40 ring-verdict-contradicted/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base font-semibold text-verdict-contradicted">
                  <AlertTriangle className="size-4" aria-hidden />
                  Conflicts in the documents ({report.conflicts.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {report.conflicts.map((c, i) => (
                  <p key={i} className="text-sm leading-relaxed">
                    {c}
                  </p>
                ))}
              </CardContent>
            </Card>
          )}

          <Card className="fade-up" style={{ animationDelay: "140ms" }}>
            <CardHeader className="border-b border-border/60 pb-4">
              <CardTitle className="text-base font-semibold">Verified skill matrix</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Requirement</TableHead>
                    <TableHead>Importance</TableHead>
                    <TableHead>Verdict</TableHead>
                    <TableHead>Evidence</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.matrix.map((row) => (
                    <TableRow key={row.requirement_id}>
                      <TableCell className="font-medium">{row.skill}</TableCell>
                      <TableCell>
                        <ImportanceBadge importance={row.importance} />
                      </TableCell>
                      <TableCell>
                        <VerdictBadge verdict={row.best_verdict} />
                      </TableCell>
                      <TableCell className="space-y-1 text-sm text-muted-foreground">
                        {row.evidence_summaries.length === 0 && "No public/internal artifact. Not asked — probe live."}
                        {row.evidence_summaries.map((s, i) => (
                          <div key={i}>
                            {s}
                            {row.evidence_urls[i] && (
                              <a
                                href={row.evidence_urls[i]}
                                target="_blank"
                                rel="noreferrer"
                                className="ml-1 inline-flex items-center gap-0.5 text-primary hover:underline"
                              >
                                source
                                <ExternalLink className="size-3" aria-hidden />
                              </a>
                            )}
                          </div>
                        ))}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <div className="fade-up grid gap-4 md:grid-cols-2" style={{ animationDelay: "180ms" }}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base font-semibold">
                  <CheckCircle2 className="size-4 text-verdict-verified" aria-hidden />
                  Technical strengths
                </CardTitle>
              </CardHeader>
              <CardContent>
                {report.technical_strengths.length === 0 && <p className="text-sm text-muted-foreground">None verified yet.</p>}
                <ul className="list-inside list-disc space-y-1.5 text-sm leading-relaxed">
                  {report.technical_strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base font-semibold">
                  <Flag className="size-4 text-verdict-partial" aria-hidden />
                  Weak areas
                </CardTitle>
              </CardHeader>
              <CardContent>
                {report.weak_areas.length === 0 && <p className="text-sm text-muted-foreground">None identified.</p>}
                <ul className="list-inside list-disc space-y-1.5 text-sm leading-relaxed">
                  {report.weak_areas.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>

          <Card className="fade-up" style={{ animationDelay: "220ms" }}>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Recommended follow-up questions</CardTitle>
              <p className="text-xs text-muted-foreground">For your live conversation — the gaps the pipeline couldn&apos;t close.</p>
            </CardHeader>
            <CardContent>
              {report.suggested_followups.length === 0 && <p className="text-sm text-muted-foreground">Nothing outstanding.</p>}
              <ul className="list-inside list-decimal space-y-1.5 text-sm leading-relaxed">
                {report.suggested_followups.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {report.transcript.length > 0 && (
            <Card className="fade-up">
              <CardHeader className="border-b border-border/60 pb-4">
                <CardTitle className="text-base font-semibold">Interview transcript</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {report.transcript.map((qa, i) => (
                  <div key={i} className="rounded-xl border border-border/70 bg-background/40 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm leading-relaxed font-medium">
                        {qa.depth > 0 && <span className="mr-1.5 text-xs font-normal text-muted-foreground">↳ follow-up</span>}
                        {qa.question_text}
                      </p>
                      {qa.specificity_verdict && <SpecificityBadge verdict={qa.specificity_verdict} />}
                    </div>
                    <p className="mt-1.5 text-xs text-muted-foreground">Why this question: {qa.rationale}</p>
                    {qa.answer_text && (
                      <p className="mt-3 rounded-lg bg-muted/60 p-3.5 text-sm leading-relaxed whitespace-pre-wrap">{qa.answer_text}</p>
                    )}
                    {qa.specificity_notes && <p className="mt-2 text-xs text-muted-foreground">{qa.specificity_notes}</p>}
                    {qa.review_flags.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {qa.review_flags.map((f, fi) => (
                          <p key={fi} className="flex items-center gap-1 text-xs font-medium text-verdict-partial">
                            <Flag className="size-3" aria-hidden />
                            {f}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          <Card className="fade-up border-primary/25 ring-primary/15">
            <CardHeader>
              <CardTitle className="text-base font-semibold">Your decision</CardTitle>
              <p className="text-xs text-muted-foreground">
                You decide. We record who, when, and why into the Evidence Ledger — nothing here is automated.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              {recordedVerdict ? (
                <p className="inline-flex items-center gap-2 rounded-lg bg-verdict-verified-bg px-3.5 py-2.5 text-sm font-medium text-verdict-verified">
                  <CheckCircle2 className="size-4" aria-hidden />
                  Decision recorded: {recordedVerdict.toUpperCase()} — sealed into the ledger.
                </p>
              ) : (
                <>
                  <Textarea
                    placeholder="Rationale (required) — this is the sentence you'd want on record a year from now."
                    value={rationale}
                    onChange={(e) => setRationale(e.target.value)}
                    rows={3}
                    disabled={recordDecision.isPending}
                  />
                  <div className="flex flex-wrap gap-2">
                    {DECISION_OPTIONS.map(({ verdict, label, icon: Icon, variant }) => (
                      <Button
                        key={verdict}
                        variant={variant}
                        disabled={!rationale.trim() || recordDecision.isPending}
                        onClick={() => {
                          setPendingVerdict(verdict);
                          recordDecision.mutate(verdict);
                        }}
                      >
                        {recordDecision.isPending && pendingVerdict === verdict ? (
                          <Loader2 className="size-4 animate-spin" aria-hidden />
                        ) : (
                          <Icon className="size-4" aria-hidden />
                        )}
                        {label}
                      </Button>
                    ))}
                  </div>
                  {recordDecision.isError && (
                    <InlineError message={friendlyError(recordDecision.error, "Couldn't record the decision. Please try again.")} />
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === "ledger" && <LedgerPanel candidateId={candidateId} />}
    </div>
  );
}
