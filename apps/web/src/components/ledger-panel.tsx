"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, Cog, FileText, Link2, ShieldAlert, ShieldCheck, User, UserRound } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/states";
import { useApi } from "@/hooks/use-api";
import type { LedgerActorType, LedgerEvent } from "@/lib/api-types";
import { friendlyError } from "@/lib/errors";
import { cn } from "@/lib/utils";

/** The Evidence Ledger: every event in this candidate's verification, hash-chained so the
 * record itself is tamper-evident. This panel is deliberately literal — real hashes, real
 * sequence numbers — because its audience is "prove to me how this decision was reached." */

const EVENT_LABELS: Record<string, string> = {
  candidate_created: "Candidate added",
  resume_ingested: "Resume ingested & fingerprinted",
  claims_extracted: "Claims extracted from resume",
  consistency_checked: "Internal consistency checked",
  github_evidence: "GitHub evidence gathered",
  interview_created: "Interview issued",
  question_asked: "Interview question generated",
  answer_recorded: "Candidate answer recorded",
  interview_submitted: "Interview submitted",
  decision_recorded: "Human decision recorded",
};

const ACTOR_META: Record<LedgerActorType, { icon: typeof User; label: string }> = {
  human: { icon: User, label: "Recruiter" },
  candidate: { icon: UserRound, label: "Candidate" },
  model: { icon: Bot, label: "AI model" },
  system: { icon: Cog, label: "System" },
};

function eventDetail(event: LedgerEvent): string | null {
  const p = event.payload;
  switch (event.event_type) {
    case "resume_ingested":
      return `${p.filename} — SHA-256 ${String(p.file_sha256).slice(0, 12)}…`;
    case "claims_extracted":
      return `${p.claim_count} claims kept, ${p.discarded_uncitable} discarded as uncitable`;
    case "consistency_checked":
      return `${p.claims_checked} claims checked, ${p.contradictions_found} contradiction${p.contradictions_found === 1 ? "" : "s"}`;
    case "github_evidence":
      return `@${p.github_login} — ${p.evidence_count} evidence item${p.evidence_count === 1 ? "" : "s"}`;
    case "interview_created":
      return `${p.target_claim_count} unverified claim${p.target_claim_count === 1 ? "" : "s"} targeted`;
    case "question_asked":
      return `Question ${Number(p.ordinal) + 1}${Number(p.depth) > 0 ? ` (follow-up, depth ${p.depth})` : ""}`;
    case "answer_recorded":
      return `Judged ${p.specificity_verdict}${Array.isArray(p.review_flags) && p.review_flags.length > 0 ? ` — ${p.review_flags.length} review flag(s)` : ""}`;
    case "interview_submitted":
      return `${p.questions_answered} questions answered`;
    case "decision_recorded":
      return `Verdict: ${String(p.verdict).toUpperCase()}`;
    default:
      return null;
  }
}

export function LedgerPanel({ candidateId }: { candidateId: string }) {
  const api = useApi();
  const ledgerQuery = useQuery({ queryKey: ["ledger", candidateId], queryFn: () => api.getLedger(candidateId) });
  const verifyQuery = useQuery({ queryKey: ["ledger-verify", candidateId], queryFn: () => api.verifyLedger(candidateId) });

  if (ledgerQuery.isLoading) return <Skeleton className="h-64 rounded-xl" />;
  if (ledgerQuery.isError || !ledgerQuery.data) {
    return (
      <ErrorState
        title="Couldn't load the evidence ledger"
        message={friendlyError(ledgerQuery.error)}
        onRetry={() => ledgerQuery.refetch()}
        retrying={ledgerQuery.isRefetching}
      />
    );
  }

  const events = ledgerQuery.data.events;
  const verification = verifyQuery.data;

  return (
    <Card className="fade-up">
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-4">
        <div>
          <CardTitle className="flex items-center gap-2 text-base font-semibold">
            <Link2 className="size-4 text-primary" aria-hidden />
            Evidence Ledger
          </CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            Append-only, hash-chained record of this verification. Any after-the-fact edit breaks the chain.
          </p>
        </div>
        {verifyQuery.isLoading && <Skeleton className="h-7 w-40 rounded-full" />}
        {verification &&
          (verification.ok ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-verdict-verified-bg px-3 py-1 text-xs font-medium text-verdict-verified">
              <ShieldCheck className="size-4" aria-hidden />
              Chain intact — {verification.event_count} events replayed
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-verdict-contradicted-bg px-3 py-1 text-xs font-medium text-verdict-contradicted">
              <ShieldAlert className="size-4" aria-hidden />
              {verification.first_broken_seq !== null
                ? `Chain broken at event #${verification.first_broken_seq}`
                : `Content altered after recording (${verification.content_mismatches.length})`}
            </span>
          ))}
      </CardHeader>
      <CardContent>
        {events.length === 0 && <p className="text-sm text-muted-foreground">No events yet.</p>}
        <ol className="relative space-y-0">
          {events.map((event, i) => {
            const actor = ACTOR_META[event.actor_type] ?? ACTOR_META.system;
            const ActorIcon = actor.icon;
            const detail = eventDetail(event);
            const mismatch = verification?.content_mismatches.find((m) => m.seq === event.seq);
            const broken = verification && !verification.ok && verification.first_broken_seq !== null && event.seq >= verification.first_broken_seq;
            return (
              <li key={event.seq} className="relative flex gap-3 pb-5 last:pb-0">
                {i < events.length - 1 && (
                  <span className="absolute top-7 left-[13px] h-full w-px bg-border" aria-hidden />
                )}
                <span
                  className={cn(
                    "z-10 mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full border bg-card",
                    mismatch || broken ? "border-verdict-contradicted text-verdict-contradicted" : "text-muted-foreground",
                  )}
                >
                  <ActorIcon className="size-3.5" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <span className="text-sm font-medium">
                      {EVENT_LABELS[event.event_type] ?? event.event_type}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {actor.label}
                      {event.actor_id ? ` · ${event.actor_id}` : ""} ·{" "}
                      {new Date(event.created_at).toLocaleString()}
                    </span>
                  </div>
                  {detail && <p className="mt-0.5 text-xs text-muted-foreground">{detail}</p>}
                  {mismatch && (
                    <p className="mt-1 text-xs font-medium text-verdict-contradicted">⚠ {mismatch.problem}</p>
                  )}
                  <p className="tabular mt-1 truncate font-mono text-[10px] text-muted-foreground/70">
                    #{event.seq} · {event.event_hash.slice(0, 16)}… ← {event.prev_hash.slice(0, 16)}…
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
        {events.length > 0 && (
          <p className="mt-4 flex items-center gap-1.5 border-t pt-3 text-xs text-muted-foreground">
            <FileText className="size-3.5 shrink-0" aria-hidden />
            Free text (answers, rationales) is attested by SHA-256 — editing a stored answer after the fact is
            detected on the next verification, even though the text itself lives outside the ledger.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
