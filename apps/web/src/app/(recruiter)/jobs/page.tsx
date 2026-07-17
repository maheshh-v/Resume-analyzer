"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Briefcase, Loader2, Plus, RotateCw, Sparkles, Users } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState, ErrorState, InlineError } from "@/components/states";
import { useApi } from "@/hooks/use-api";
import { friendlyError } from "@/lib/errors";

export default function JobsPage() {
  const api = useApi();
  const queryClient = useQueryClient();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [jdRaw, setJdRaw] = useState("");

  const jobsQuery = useQuery({ queryKey: ["jobs"], queryFn: api.listJobs });

  const createJob = useMutation({
    mutationFn: () => api.createJob({ title, jd_raw: jdRaw }),
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      // Deliberately keep the dialog open in its "opening job" state — navigation
      // unmounts this page, so the user never sees a dead gap without feedback.
      router.push(`/jobs/${job.id}`);
    },
  });

  // Extraction takes several seconds; the dialog must not be dismissable mid-flight or the
  // user loses the context (the mutation itself would still finish and navigate).
  const dialogLocked = createJob.isPending || createJob.isSuccess;

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen && dialogLocked) return;
    setOpen(nextOpen);
    if (!nextOpen) {
      createJob.reset();
      setTitle("");
      setJdRaw("");
    }
  }

  const newJobDialog = (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          <Button>
            <Plus className="size-4" aria-hidden />
            New job
          </Button>
        }
      />
      <DialogContent className="sm:max-w-lg" showCloseButton={!dialogLocked}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createJob.mutate();
          }}
        >
          <DialogHeader>
            <DialogTitle>Create a job</DialogTitle>
            <DialogDescription>
              We&apos;ll extract structured requirements from the JD. You&apos;ll review and edit them before anything else runs.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="title">Job title</Label>
              <Input
                id="title"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Senior Backend Engineer"
                disabled={dialogLocked}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="jd">Job description</Label>
              <Textarea
                id="jd"
                required
                rows={10}
                value={jdRaw}
                onChange={(e) => setJdRaw(e.target.value)}
                placeholder="Paste the full job description..."
                disabled={dialogLocked}
              />
            </div>

            {createJob.isPending && (
              <div className="flex items-center gap-2.5 rounded-lg bg-primary/[0.06] px-3 py-2.5 text-sm text-primary ring-1 ring-primary/10">
                <Sparkles className="size-4 shrink-0 animate-pulse" aria-hidden />
                Reading the JD and extracting verifiable requirements — this usually takes 5–15 seconds.
              </div>
            )}

            {createJob.isError && (
              <div className="space-y-2.5 rounded-lg bg-destructive/[0.06] px-3 py-2.5 ring-1 ring-destructive/15">
                <InlineError message={friendlyError(createJob.error, "We couldn't create this job. Please try again.")} />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => createJob.mutate()}
                >
                  <RotateCw className="size-3.5" aria-hidden />
                  Retry
                </Button>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button type="submit" disabled={dialogLocked || !title.trim() || !jdRaw.trim()}>
              {dialogLocked && <Loader2 className="size-4 animate-spin" aria-hidden />}
              {createJob.isSuccess ? "Opening job..." : createJob.isPending ? "Extracting requirements..." : "Create job"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );

  return (
    <div className="space-y-8">
      <div className="fade-up flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-[1.75rem] font-semibold tracking-tight">Jobs</h1>
          <p className="text-sm text-muted-foreground">
            Paste a job description to extract what&apos;s actually worth verifying.
          </p>
        </div>
        {newJobDialog}
      </div>

      {jobsQuery.isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-3 rounded-xl bg-card p-5 shadow-card ring-1 ring-foreground/[0.07]">
              <Skeleton className="h-5 w-3/4 rounded-md" />
              <Skeleton className="h-4 w-1/3 rounded-md" />
              <Skeleton className="h-4 w-1/2 rounded-md" />
            </div>
          ))}
        </div>
      )}

      {jobsQuery.isError && (
        <ErrorState
          title="Couldn't load your jobs"
          message={friendlyError(jobsQuery.error)}
          onRetry={() => jobsQuery.refetch()}
          retrying={jobsQuery.isRefetching}
        />
      )}

      {jobsQuery.data && jobsQuery.data.length === 0 && (
        <EmptyState
          icon={Briefcase}
          title="No jobs yet"
          body="Create your first job — paste the JD and we'll turn it into a reviewable list of verifiable requirements."
          action={
            <Button onClick={() => setOpen(true)}>
              <Plus className="size-4" aria-hidden />
              Create your first job
            </Button>
          }
          className="fade-up"
        />
      )}

      {jobsQuery.data && jobsQuery.data.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {jobsQuery.data.map((job, i) => (
            <Link key={job.id} href={`/jobs/${job.id}`} className="group fade-up" style={{ animationDelay: `${i * 60}ms` }}>
              <Card className="h-full transition-all duration-300 group-hover:-translate-y-1 group-hover:shadow-lift group-hover:ring-primary/25">
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <CardTitle className="text-base leading-snug font-semibold">{job.title}</CardTitle>
                    <ArrowUpRight
                      className="size-4 shrink-0 text-muted-foreground/50 transition-all duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-primary"
                      aria-hidden
                    />
                  </div>
                  <Badge variant={job.requirements_status === "reviewed" ? "default" : "secondary"} className="w-fit">
                    {job.requirements_status === "reviewed" ? "Reviewed" : "Draft"}
                  </Badge>
                </CardHeader>
                <CardContent className="mt-auto flex items-center justify-between border-t border-border/60 pt-3 text-sm text-muted-foreground">
                  <span className="inline-flex items-center gap-1.5">
                    <Users className="size-4" aria-hidden />
                    {job.candidate_count} candidate{job.candidate_count === 1 ? "" : "s"}
                  </span>
                  <span className="tabular text-xs">{new Date(job.created_at).toLocaleDateString()}</span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
