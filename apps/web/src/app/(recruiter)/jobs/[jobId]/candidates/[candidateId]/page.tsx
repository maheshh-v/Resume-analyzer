"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import type { Evidence, EvidenceVerdict, MatchRow } from "@/lib/api-types";

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

function matchStatusVariant(status: MatchRow["status"]) {
  switch (status) {
    case "matched":
      return "default" as const;
    case "partial":
      return "secondary" as const;
    default:
      return "outline" as const;
  }
}

export default function CandidateDetailPage() {
  const { jobId, candidateId } = useParams<{ jobId: string; candidateId: string }>();
  const api = useApi();
  const [interviewLink, setInterviewLink] = useState<string | null>(null);

  const detailQuery = useQuery({ queryKey: ["candidate", candidateId], queryFn: () => api.getCandidateDetail(candidateId) });

  const createInterview = useMutation({
    mutationFn: () => api.createInterview(candidateId),
    onSuccess: (interview) => {
      const origin = typeof window !== "undefined" ? window.location.origin : "";
      setInterviewLink(`${origin}${interview.interview_url_path}`);
    },
  });

  if (detailQuery.isLoading) {
    return <Skeleton className="h-96 rounded-lg" />;
  }
  if (detailQuery.isError || !detailQuery.data) {
    return <p className="text-sm text-destructive">Failed to load candidate.</p>;
  }

  const { candidate, claims, evidence, matches } = detailQuery.data;
  const evidenceByClaim = new Map<string, Evidence[]>();
  for (const e of evidence) {
    evidenceByClaim.set(e.claim_id, [...(evidenceByClaim.get(e.claim_id) ?? []), e]);
  }
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{candidate.name}</h1>
          {candidate.email && <p className="text-sm text-muted-foreground">{candidate.email}</p>}
        </div>
        <div className="flex gap-2">
          <Link href={`/jobs/${jobId}/candidates/${candidateId}/report`}>
            <Button variant="outline">Hiring summary</Button>
          </Link>
          <Button onClick={() => createInterview.mutate()} disabled={createInterview.isPending}>
            {createInterview.isPending ? "Generating..." : "Generate interview"}
          </Button>
        </div>
      </div>

      {createInterview.isError && (
        <p className="text-sm text-destructive">{(createInterview.error as Error).message}</p>
      )}
      {interviewLink && (
        <Card>
          <CardContent className="flex items-center justify-between gap-4 py-4">
            <div className="min-w-0">
              <p className="text-sm font-medium">Interview link ready — send this to the candidate.</p>
              <p className="truncate text-sm text-muted-foreground">{interviewLink}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigator.clipboard.writeText(interviewLink)}
            >
              Copy link
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">JD match</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
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
                    <Badge variant={m.importance === "must_have" ? "default" : "outline"}>{m.importance.replace("_", " ")}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={matchStatusVariant(m.status)}>{m.status}</Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{m.note}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Claims &amp; evidence</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {claims.length === 0 && <p className="text-sm text-muted-foreground">No claims extracted.</p>}
          {claims.map((claim) => (
            <div key={claim.id} className="rounded-lg border p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{claim.claim_type}</Badge>
                <p className="text-sm font-medium">{claim.claim_text}</p>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {(evidenceByClaim.get(claim.id) ?? []).map((e) => (
                  <div key={e.id} className="flex items-center gap-2 rounded-md bg-muted px-2 py-1 text-xs">
                    <Badge variant={verdictBadgeVariant(e.verdict)}>{e.verdict}</Badge>
                    <span>{e.summary}</span>
                    {e.artifact_url && (
                      <a href={e.artifact_url} target="_blank" rel="noreferrer" className="text-primary underline">
                        source ↗
                      </a>
                    )}
                  </div>
                ))}
                {!evidenceByClaim.get(claim.id) && (
                  <span className="text-xs text-muted-foreground">No evidence gathered yet — unverified, not a strike against them.</span>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
