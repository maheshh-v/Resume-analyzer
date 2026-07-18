import { CheckCircle2, ExternalLink, FileSearch, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ThemeToggle } from "@/components/theme-toggle";
import { API_BASE } from "@/lib/api-client";

// Results change whenever the harness re-runs; never cache this at build time.
export const dynamic = "force-dynamic";

export const metadata = {
  title: "Benchmarks — Recruit",
  description: "Reproducible accuracy numbers for the evidence pipeline. No marketing, just the measurements.",
};

type Metrics = {
  claim_extraction?: { precision: number; recall: number; f1: number; tp: number; fp: number; fn: number };
  citation_validity?: {
    span_citation_validity: number;
    accepted_claims_checked: number;
    invalid_span_citations: number;
    url_citations_seen: number;
  };
  verdict_accuracy?: {
    verdict_match_rate: number;
    claims_scored: number;
    fabrication_safety_rate: number;
    fabricated_claims: number;
    false_verifications: unknown[];
  };
};

type BenchmarkReport = {
  available: boolean;
  detail?: string | null;
  generated_at?: string | null;
  git_commit?: string | null;
  provider?: string | null;
  dataset?: { name: string; path: string; case_count: number; buckets: Record<string, number> } | null;
  metrics?: Metrics;
  markdown?: string | null;
  dataset_url?: string | null;
};

const DATASET_URL_FALLBACK = "https://github.com/maheshh-v/Resume-analyzer/blob/main/evals/datasets/golden_v1.jsonl";

async function getBenchmarks(): Promise<BenchmarkReport> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/benchmarks/latest`, { cache: "no-store" });
    if (!res.ok) return { available: false, detail: `Benchmarks endpoint returned ${res.status}.` };
    return (await res.json()) as BenchmarkReport;
  } catch {
    return { available: false, detail: "Couldn't reach the benchmarks endpoint." };
  }
}

function pct(value: number | undefined): string {
  return value === undefined ? "—" : `${(value * 100).toFixed(1)}%`;
}

function StatCard({
  label,
  value,
  detail,
  target,
  emphasis,
}: {
  label: string;
  value: string;
  detail: string;
  target?: boolean;
  emphasis?: boolean;
}) {
  return (
    <Card className={emphasis ? "border-primary/30 bg-primary/[0.03]" : undefined}>
      <CardHeader className="gap-1">
        <CardDescription className="flex items-center gap-1.5 text-xs uppercase tracking-wide">
          {label}
          {target && (
            <span className="inline-flex items-center gap-1 text-verdict-verified">
              <CheckCircle2 className="size-3" aria-hidden /> target met
            </span>
          )}
        </CardDescription>
        <CardTitle className="font-mono text-4xl tabular-nums">{value}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-relaxed text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  );
}

export default async function BenchmarksPage() {
  const report = await getBenchmarks();
  const datasetUrl = report.dataset_url ?? DATASET_URL_FALLBACK;
  const m = report.metrics ?? {};
  const ce = m.claim_extraction;
  const cv = m.citation_validity;
  const va = m.verdict_accuracy;
  const generated = report.generated_at ? new Date(report.generated_at).toUTCString() : null;

  return (
    <div className="ambient min-h-screen">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-6">
        <Link href="/" className="flex items-center gap-2 font-medium">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card">
            <ShieldCheck className="size-4" aria-hidden />
          </span>
          Recruit
        </Link>
        <ThemeToggle />
      </header>

      <main className="mx-auto max-w-5xl space-y-10 px-6 pb-24">
        <section className="space-y-3">
          <Badge variant="outline">Benchmarks · golden_v1</Badge>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Pipeline accuracy, measured</h1>
          <p className="max-w-2xl text-base leading-relaxed text-muted-foreground">
            Reproducible numbers for the evidence pipeline against a hand-labelled dataset — real resumes,
            planted lies, and messy edge cases. No aggregate &ldquo;match score,&rdquo; no automated hire/reject
            decision. Just how well the system extracts claims and, above all, whether it ever manufactures
            false confidence about a real person.
          </p>
        </section>

        {!report.available ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileSearch className="size-5 text-muted-foreground" aria-hidden /> No benchmark run yet
              </CardTitle>
              <CardDescription>{report.detail ?? "Run `make eval-report` to generate one."}</CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <>
            <section className="grid gap-4 sm:grid-cols-2">
              <StatCard
                label="Claim-extraction F1"
                value={pct(ce?.f1)}
                detail={`Precision ${pct(ce?.precision)}, recall ${pct(ce?.recall)} — how completely and cleanly resumes become citable claims (tp ${ce?.tp ?? 0}, fp ${ce?.fp ?? 0}, fn ${ce?.fn ?? 0}).`}
              />
              <StatCard
                label="Citation validity"
                value={pct(cv?.span_citation_validity)}
                target={cv?.span_citation_validity === 1}
                detail={`Of ${cv?.accepted_claims_checked ?? 0} accepted claims, the share whose source span resolves to a literal substring of the resume. ${cv?.invalid_span_citations ?? 0} invalid. Target is 100%.`}
              />
              <StatCard
                label="Verdict match"
                value={pct(va?.verdict_match_rate)}
                detail={`Across ${va?.claims_scored ?? 0} claims, how often the verified / not-verified outcome agrees with ground truth.`}
              />
              <StatCard
                label="Fabrication safety"
                value={pct(va?.fabrication_safety_rate)}
                target={va?.fabrication_safety_rate === 1}
                emphasis
                detail={`Of ${va?.fabricated_claims ?? 0} planted lies (fake companies, impossible tenure, fake certs), the share NOT marked verified. ${va?.false_verifications?.length ?? 0} falsely verified. The number that matters most.`}
              />
            </section>

            <section className="space-y-4">
              <h2 className="text-lg font-semibold">Methodology</h2>
              <Card>
                <CardContent className="grid gap-x-8 gap-y-4 py-6 sm:grid-cols-2">
                  <Detail term="Dataset">
                    {report.dataset?.case_count ?? 0} hand-labelled cases
                    {report.dataset?.buckets
                      ? ` (${Object.entries(report.dataset.buckets)
                          .map(([k, v]) => `${v} ${k.replace("_", " ")}`)
                          .join(", ")})`
                      : ""}
                  </Detail>
                  <Detail term="Last run">{generated ?? "—"}</Detail>
                  <Detail term="Provider">
                    <code className="font-mono text-xs">{report.provider ?? "—"}</code>{" "}
                    <span className="text-muted-foreground">
                      (offline recorded fixtures; a live model pass may differ)
                    </span>
                  </Detail>
                  <Detail term="Commit">
                    <code className="font-mono text-xs">{report.git_commit ?? "—"}</code>
                  </Detail>
                  <Detail term="Dataset source">
                    <a
                      href={datasetUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-primary hover:underline"
                    >
                      golden_v1.jsonl on GitHub <ExternalLink className="size-3" aria-hidden />
                    </a>
                  </Detail>
                </CardContent>
              </Card>
              <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
                Every claim the pipeline accepts must cite a span that literally appears in the source document;
                a claim that can&rsquo;t be cited is discarded, not kept with a weaker label. These metrics measure
                that evidence pipeline — they are not a hiring recommendation, and the system never emits one.
              </p>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function Detail({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{term}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  );
}
