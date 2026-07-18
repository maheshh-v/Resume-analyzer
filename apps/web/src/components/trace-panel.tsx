"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Cpu } from "lucide-react";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { InlineError } from "@/components/states";
import { useApi } from "@/hooks/use-api";
import type { LlmStageCost } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { friendlyError } from "@/lib/errors";

const STAGE_LABELS: Record<string, string> = {
  extract_jd: "JD → requirements",
  extract_claims: "Resume → claims",
  interview_generate_base: "Interview · base question",
  interview_generate_followup: "Interview · follow-up",
  interview_evaluate_answer: "Interview · answer scoring",
};

function stageLabel(stage: string): string {
  return STAGE_LABELS[stage] ?? stage;
}

function fmtCost(usd: number): string {
  if (usd === 0) return "$0";
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

function fmtLatency(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

/** Collapsible, recruiter-only view of what the AI pipeline cost for this candidate.
 * Technical and small by design — it's an audit/observability affordance, not a headline. */
export function TracePanel({ candidateId }: { candidateId: string }) {
  const api = useApi();
  const [open, setOpen] = useState(false);

  const costs = useQuery({
    queryKey: ["llm-costs", candidateId],
    queryFn: () => api.getLlmCosts(candidateId),
    enabled: open, // don't fetch until the recruiter opens the panel
  });

  return (
    <Card className="fade-up" style={{ animationDelay: "240ms" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-6 py-4 text-left"
      >
        <span className="flex items-center gap-2">
          <Cpu className="size-4 text-muted-foreground" aria-hidden />
          <span className="text-base font-semibold">AI pipeline trace</span>
          {costs.data && (
            <span className="text-xs text-muted-foreground">
              {costs.data.total_calls} calls · {fmtCost(costs.data.total_cost_usd)}
            </span>
          )}
        </span>
        <ChevronDown className={cn("size-4 text-muted-foreground transition-transform", open && "rotate-180")} aria-hidden />
      </button>

      {open && (
        <CardContent className="border-t border-border/60 pt-4">
          {costs.isLoading && (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full rounded-md" />
              <Skeleton className="h-8 w-full rounded-md" />
            </div>
          )}
          {costs.isError && <InlineError message={friendlyError(costs.error, "Couldn't load the trace.")} />}
          {costs.data && costs.data.per_stage.length === 0 && (
            <p className="py-3 text-sm text-muted-foreground">
              No model calls recorded for this candidate yet.
            </p>
          )}
          {costs.data && costs.data.per_stage.length > 0 && (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead>Stage</TableHead>
                      <TableHead>Model</TableHead>
                      <TableHead className="text-right">Calls</TableHead>
                      <TableHead className="text-right">Tokens (in/out)</TableHead>
                      <TableHead className="text-right">Time</TableHead>
                      <TableHead className="text-right">Retries</TableHead>
                      <TableHead className="text-right">Cost</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {costs.data.per_stage.map((s: LlmStageCost) => (
                      <TableRow key={s.pipeline_stage}>
                        <TableCell className="font-medium">{stageLabel(s.pipeline_stage)}</TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">{s.models.join(", ")}</TableCell>
                        <TableCell className="text-right tabular-nums">{s.calls}</TableCell>
                        <TableCell className="text-right tabular-nums text-muted-foreground">
                          {s.input_tokens.toLocaleString()} / {s.output_tokens.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{fmtLatency(s.latency_ms_total)}</TableCell>
                        <TableCell className="text-right tabular-nums">{s.max_retry_count}</TableCell>
                        <TableCell className="text-right tabular-nums">{fmtCost(s.cost_usd)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="text-muted-foreground">
                  {costs.data.total_input_tokens.toLocaleString()} in / {costs.data.total_output_tokens.toLocaleString()} out
                  tokens · {fmtLatency(costs.data.total_latency_ms)} total
                </span>
                <span className="font-medium">
                  Total cost <span className="font-mono">{fmtCost(costs.data.total_cost_usd)}</span>
                </span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Metadata only — prompts and responses are never stored. Cost is a best-effort estimate.
              </p>
            </>
          )}
        </CardContent>
      )}
    </Card>
  );
}
