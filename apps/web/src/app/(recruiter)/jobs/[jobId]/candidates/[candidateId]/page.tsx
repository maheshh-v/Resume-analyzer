"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Check, Copy, ExternalLink, FileCheck2, Loader2, MessageSquareText } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ErrorState, InlineError } from "@/components/states";
import { TracePanel } from "@/components/trace-panel";
import { ImportanceBadge, MatchBadge, VerdictBadge } from "@/components/verdict-badge";
import { useApi } from "@/hooks/use-api";
import type { Evidence } from "@/lib/api-types";
import { friendlyError } from "@/lib/errors";

export default function CandidateDetailPage() {
  const { jobId, candidateId } = useParams<{ jobId: string; candidateId: string }>();
  const api = useApi();
  const [interviewLink, setInterviewLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);

  const detailQuery = useQuery({ queryKey: ["candidate", candidateId], queryFn: () => api.getCandidateDetail(candidateId) });

  const createInterview = useMutation({
    mutationFn: () => api.createInterview(candidateId),
    onSuccess: (interview) => {
      const origin = typeof window !== "undefined" ? window.location.origin : "";
      setInterviewLink(`${origin}${interview.interview_url_path}`);
    },
  });

  if (detailQuery.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-28 rounded-md" />
        <Skeleton className="h-9 w-1/2 rounded-md" />
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }
  if (detailQuery.isError || !detailQuery.data) {
    return (
      <ErrorState
        title="Couldn't load this candidate"
        message={friendlyError(detailQuery.error)}
        onRetry={() => detailQuery.refetch()}
        retrying={detailQuery.isRefetching}
      />
    );
  }

  const { candidate, claims, evidence, matches } = detailQuery.data;
  const evidenceByClaim = new Map<string, Evidence[]>();
  for (const e of evidence) {
    evidenceByClaim.set(e.claim_id, [...(evidenceByClaim.get(e.claim_id) ?? []), e]);
  }

  async function copyLink() {
    if (!interviewLink) return;
    try {
      await navigator.clipboard.writeText(interviewLink);
      setCopied(true);
      setCopyError(false);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopyError(true); // clipboard can be blocked (permissions/insecure context)
    }
  }

  return (
    <div className="space-y-6">
      <div className="fade-up flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href={`/jobs/${jobId}`}
            className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" aria-hidden />
            Back to job
          </Link>
          <h1 className="text-[1.75rem] font-semibold tracking-tight">{candidate.name}</h1>
          {candidate.email && <p className="mt-0.5 text-sm text-muted-foreground">{candidate.email}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/jobs/${jobId}/candidates/${candidateId}/report`}>
            <Button variant="outline">
              <FileCheck2 className="size-4" aria-hidden />
              Hiring summary
            </Button>
          </Link>
          <Button onClick={() => createInterview.mutate()} disabled={createInterview.isPending}>
            {createInterview.isPending ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <MessageSquareText className="size-4" aria-hidden />
            )}
            {createInterview.isPending ? "Generating..." : "Generate interview"}
          </Button>
        </div>
      </div>

      {createInterview.isError && (
        <InlineError message={friendlyError(createInterview.error, "Couldn't generate the interview. Please try again.")} />
      )}
      {interviewLink && (
        <Card className="fade-up border-primary/25 bg-primary/[0.04] ring-primary/20">
          <CardContent className="flex flex-wrap items-center justify-between gap-4 py-4">
            <div className="min-w-0 space-y-1">
              <p className="text-sm font-medium">Interview link ready — send this to the candidate.</p>
              <p className="truncate font-mono text-xs text-muted-foreground">{interviewLink}</p>
              {copyError && <p className="text-xs text-destructive">Couldn&apos;t copy automatically — select the link above and copy it manually.</p>}
            </div>
            <Button variant="outline" size="sm" onClick={copyLink}>
              {copied ? <Check className="size-3.5 text-verdict-verified" aria-hidden /> : <Copy className="size-3.5" aria-hidden />}
              {copied ? "Copied" : "Copy link"}
            </Button>
          </CardContent>
        </Card>
      )}

      <Card className="fade-up" style={{ animationDelay: "80ms" }}>
        <CardHeader className="border-b border-border/60 pb-4">
          <CardTitle className="text-base font-semibold">JD match</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Requirement</TableHead>
                <TableHead>Importance</TableHead>
                <TableHead>Match</TableHead>
                <TableHead>Note</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {matches.map((m) => (
                <TableRow key={m.requirement_id}>
                  <TableCell className="font-medium">{m.skill}</TableCell>
                  <TableCell>
                    <ImportanceBadge importance={m.importance} />
                  </TableCell>
                  <TableCell>
                    <MatchBadge status={m.status} />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{m.note}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="fade-up" style={{ animationDelay: "160ms" }}>
        <CardHeader className="border-b border-border/60 pb-4">
          <CardTitle className="text-base font-semibold">Claims &amp; evidence</CardTitle>
          <p className="text-xs text-muted-foreground">
            Every claim below was quoted verbatim from the resume — uncitable claims were discarded at extraction.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          {claims.length === 0 && <p className="py-4 text-center text-sm text-muted-foreground">No claims extracted.</p>}
          {claims.map((claim) => (
            <div
              key={claim.id}
              className="rounded-xl border border-border/70 bg-background/40 p-4 transition-colors duration-200 hover:border-border"
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="capitalize">
                  {claim.claim_type}
                </Badge>
                <p className="text-sm font-medium">{claim.claim_text}</p>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {(evidenceByClaim.get(claim.id) ?? []).map((e) => (
                  <div key={e.id} className="flex items-center gap-2 rounded-lg bg-muted/80 px-2.5 py-1.5 text-xs">
                    <VerdictBadge verdict={e.verdict} />
                    <span>{e.summary}</span>
                    {e.artifact_url && (
                      <a
                        href={e.artifact_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-0.5 font-medium text-primary hover:underline"
                      >
                        source
                        <ExternalLink className="size-3" aria-hidden />
                      </a>
                    )}
                  </div>
                ))}
                {!evidenceByClaim.get(claim.id) && (
                  <span className="text-xs text-muted-foreground">
                    No evidence gathered yet — unverified, not a strike against them.
                  </span>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <TracePanel candidateId={candidateId} />
    </div>
  );
}
