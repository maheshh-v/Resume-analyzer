"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
import { useApi } from "@/hooks/use-api";

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
      setOpen(false);
      setTitle("");
      setJdRaw("");
      router.push(`/jobs/${job.id}`);
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Jobs</h1>
          <p className="text-sm text-muted-foreground">Paste a job description to extract what&apos;s actually worth verifying.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger render={<Button>New job</Button>} />
          <DialogContent className="sm:max-w-lg">
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
                  <Input id="title" required value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Senior Backend Engineer" />
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
                  />
                </div>
                {createJob.isError && <p className="text-sm text-destructive">{(createJob.error as Error).message}</p>}
              </div>
              <DialogFooter>
                <Button type="submit" disabled={createJob.isPending}>
                  {createJob.isPending ? "Extracting requirements..." : "Create job"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {jobsQuery.isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32 rounded-lg" />
          ))}
        </div>
      )}

      {jobsQuery.isError && <p className="text-sm text-destructive">Failed to load jobs: {(jobsQuery.error as Error).message}</p>}

      {jobsQuery.data && jobsQuery.data.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No jobs yet. Create one to get started.
          </CardContent>
        </Card>
      )}

      {jobsQuery.data && jobsQuery.data.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {jobsQuery.data.map((job) => (
            <Link key={job.id} href={`/jobs/${job.id}`}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardHeader>
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-base">{job.title}</CardTitle>
                    <Badge variant={job.requirements_status === "reviewed" ? "default" : "secondary"}>
                      {job.requirements_status === "reviewed" ? "Reviewed" : "Draft"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {job.candidate_count} candidate{job.candidate_count === 1 ? "" : "s"}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
