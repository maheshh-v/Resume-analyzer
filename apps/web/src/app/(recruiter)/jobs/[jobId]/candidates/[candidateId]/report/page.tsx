"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useApi } from "@/hooks/use-api";
import type { EvidenceVerdict } from "@/lib/api-types";

function verdictBadgeVariant(verdict: EvidenceVerdict) {
  switch (verdict) {
    case "verified":
      return "default" as const;
    case "contradicted":
      return "destructive" as const;
    case "partial":
      return "secondary" as const;
    default:
      return "outline" as const;
  }
}

export default function HiringSummaryPage() {
  const { candidateId } = useParams<{ jobId: string; candidateId: string }>();
  const api = useApi();
  const [rationale, setRationale] = useState("");
  const [recordedVerdict, setRecordedVerdict] = useState<string | null>(null);

  const reportQuery = useQuery({ queryKey: ["report", candidateId], queryFn: () => api.getReport(candidateId) });

  const recordDecision = useMutation({
    mutationFn: (verdict: string) => api.recordDecision(candidateId, { verdict, rationale }),
    onSuccess: (decision) => setRecordedVerdict(decision.verdict),
  });

  if (reportQuery.isLoading) return <Skeleton className="h-96 rounded-lg" />;
  if (reportQuery.isError || !reportQuery.data) return <p className="text-sm text-destructive">Failed to load report.</p>;

  const report = reportQuery.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Hiring summary</h1>
        <p className="text-sm text-muted-foreground">Every verdict below is cited. Nothing here is a score, ranking, or recommendation.</p>
      </div>

      <Card>
        <CardContent className="space-y-2 py-4">
          <div className="flex items-center gap-3">
            <span className="text-lg font-semibold">
              {report.evidence_coverage_count} of {report.evidence_coverage_total}
            </span>
            <span className="text-sm text-muted-foreground">requirements have supporting evidence</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-primary"
              style={{
                width: `${report.evidence_coverage_total === 0 ? 0 : (report.evidence_coverage_count / report.evidence_coverage_total) * 100}%`,
              }}
            />
          </div>
          <p className="text-xs text-muted-foreground">{report.evidence_coverage_note}</p>
        </CardContent>
      </Card>

      {report.conflicts.length > 0 && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-base text-destructive">Conflicts in the documents ({report.conflicts.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {report.conflicts.map((c, i) => (
              <p key={i} className="text-sm">
                {c}
              </p>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Verified skill matrix</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
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
                    <Badge variant={row.importance === "must_have" ? "default" : "outline"}>{row.importance.replace("_", " ")}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={verdictBadgeVariant(row.best_verdict)}>{row.best_verdict}</Badge>
                  </TableCell>
                  <TableCell className="space-y-1 text-sm text-muted-foreground">
                    {row.evidence_summaries.length === 0 && "No public/internal artifact. Not asked — probe live."}
                    {row.evidence_summaries.map((s, i) => (
                      <div key={i}>
                        {s}
                        {row.evidence_urls[i] && (
                          <>
                            {" "}
                            <a href={row.evidence_urls[i]} target="_blank" rel="noreferrer" className="text-primary underline">
                              ↗
                            </a>
                          </>
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

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Technical strengths</CardTitle>
          </CardHeader>
          <CardContent>
            {report.technical_strengths.length === 0 && <p className="text-sm text-muted-foreground">None verified yet.</p>}
            <ul className="list-inside list-disc space-y-1 text-sm">
              {report.technical_strengths.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Weak areas</CardTitle>
          </CardHeader>
          <CardContent>
            {report.weak_areas.length === 0 && <p className="text-sm text-muted-foreground">None identified.</p>}
            <ul className="list-inside list-disc space-y-1 text-sm">
              {report.weak_areas.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recommended follow-up questions</CardTitle>
        </CardHeader>
        <CardContent>
          {report.suggested_followups.length === 0 && <p className="text-sm text-muted-foreground">Nothing outstanding.</p>}
          <ul className="list-inside list-decimal space-y-1 text-sm">
            {report.suggested_followups.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {report.transcript.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Interview transcript</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {report.transcript.map((qa, i) => (
              <div key={i} className="rounded-lg border p-4">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{qa.question_text}</p>
                  {qa.specificity_verdict && (
                    <Badge variant={qa.specificity_verdict === "strong" ? "default" : "secondary"}>{qa.specificity_verdict}</Badge>
                  )}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">Why this question: {qa.rationale}</p>
                {qa.answer_text && <p className="mt-2 text-sm">{qa.answer_text}</p>}
                {qa.specificity_notes && <p className="mt-1 text-xs text-muted-foreground">{qa.specificity_notes}</p>}
                {qa.review_flags.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {qa.review_flags.map((f, fi) => (
                      <p key={fi} className="text-xs text-amber-600">
                        ⚑ {f}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Your decision</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground">You decide. We record who, when, and why — nothing here is automated.</p>
          {recordedVerdict ? (
            <p className="text-sm font-medium">Recorded: {recordedVerdict}</p>
          ) : (
            <>
              <Textarea
                placeholder="Rationale (required)"
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                rows={3}
              />
              <div className="flex gap-2">
                <Button disabled={!rationale || recordDecision.isPending} onClick={() => recordDecision.mutate("advance")}>
                  Advance
                </Button>
                <Button variant="secondary" disabled={!rationale || recordDecision.isPending} onClick={() => recordDecision.mutate("hold")}>
                  Hold
                </Button>
                <Button variant="destructive" disabled={!rationale || recordDecision.isPending} onClick={() => recordDecision.mutate("decline")}>
                  Decline
                </Button>
              </div>
              {recordDecision.isError && <p className="text-sm text-destructive">{(recordDecision.error as Error).message}</p>}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
