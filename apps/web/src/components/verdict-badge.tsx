import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  CircleHelp,
  MinusCircle,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import type { EvidenceVerdict, MatchRow } from "@/lib/api-types";
import { cn } from "@/lib/utils";

/** Every evidence verdict in the app renders through here: one icon + color pairing,
 * never color alone (color-blind safe), never a number (verdicts are not scores). */

const VERDICT_STYLES: Record<EvidenceVerdict, { icon: typeof CheckCircle2; className: string; label: string }> = {
  verified: {
    icon: CheckCircle2,
    className: "bg-verdict-verified-bg text-verdict-verified",
    label: "Verified",
  },
  partial: {
    icon: CircleDashed,
    className: "bg-verdict-partial-bg text-verdict-partial",
    label: "Partial",
  },
  unverified: {
    icon: CircleHelp,
    className: "bg-verdict-unverified-bg text-verdict-unverified",
    label: "Unverified",
  },
  contradicted: {
    icon: AlertTriangle,
    className: "bg-verdict-contradicted-bg text-verdict-contradicted",
    label: "Contradicted",
  },
};

export function VerdictBadge({ verdict, className }: { verdict: EvidenceVerdict; className?: string }) {
  const style = VERDICT_STYLES[verdict] ?? VERDICT_STYLES.unverified;
  const Icon = style.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        style.className,
        className,
      )}
    >
      <Icon className="size-3.5 shrink-0" aria-hidden />
      {style.label}
    </span>
  );
}

const MATCH_STYLES: Record<MatchRow["status"], { icon: typeof CheckCircle2; className: string; label: string }> = {
  matched: { icon: CheckCircle2, className: "bg-verdict-verified-bg text-verdict-verified", label: "Matched" },
  partial: { icon: CircleDashed, className: "bg-verdict-partial-bg text-verdict-partial", label: "Partial" },
  gap: { icon: MinusCircle, className: "bg-verdict-unverified-bg text-verdict-unverified", label: "Gap" },
};

export function MatchBadge({ status, className }: { status: MatchRow["status"]; className?: string }) {
  const style = MATCH_STYLES[status] ?? MATCH_STYLES.gap;
  const Icon = style.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        style.className,
        className,
      )}
    >
      <Icon className="size-3.5 shrink-0" aria-hidden />
      {style.label}
    </span>
  );
}

export function SpecificityBadge({ verdict, className }: { verdict: "strong" | "weak"; className?: string }) {
  const strong = verdict === "strong";
  const Icon = strong ? ThumbsUp : ThumbsDown;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        strong ? "bg-verdict-verified-bg text-verdict-verified" : "bg-verdict-partial-bg text-verdict-partial",
        className,
      )}
    >
      <Icon className="size-3.5 shrink-0" aria-hidden />
      {strong ? "Specific" : "Vague"}
    </span>
  );
}

export function ImportanceBadge({ importance, className }: { importance: string; className?: string }) {
  const must = importance === "must_have";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        must ? "bg-primary/10 text-primary" : "border border-border text-muted-foreground",
        className,
      )}
    >
      {must ? "Must-have" : "Nice-to-have"}
    </span>
  );
}
