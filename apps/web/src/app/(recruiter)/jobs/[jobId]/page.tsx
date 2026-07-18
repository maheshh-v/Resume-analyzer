"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Loader2,
  Plus,
  Save,
  Trash2,
  Upload,
  UserPlus,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApplyLinkDialog, BulkUploadZone, ImportSheetDialog } from "@/components/intake";
import { EmptyState, ErrorState, InlineError } from "@/components/states";
import { useApi } from "@/hooks/use-api";
import type { RequirementInput } from "@/lib/api-client";
import type { Candidate } from "@/lib/api-types";
import { friendlyError } from "@/lib/errors";

function RequirementsEditor({ jobId, requirements, reviewed }: { jobId: string; requirements: RequirementInput[]; reviewed: boolean }) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [rows, setRows] = useState<RequirementInput[]>(requirements);

  const save = useMutation({
    mutationFn: () => api.replaceRequirements(jobId, rows),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs", jobId] }),
  });

  function updateRow(index: number, patch: Partial<RequirementInput>) {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function removeRow(index: number) {
    setRows((prev) => prev.filter((_, i) => i !== index));
  }

  function addRow() {
    setRows((prev) => [
      ...prev,
      { skill: "", normalized_skill: "", category: "technical", importance: "nice_to_have", min_years: null, evidence_criteria: "" },
    ]);
  }

  return (
    <Card className="fade-up" style={{ animationDelay: "80ms" }}>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-4">
        <div className="space-y-0.5">
          <CardTitle className="flex items-center gap-2 text-base font-semibold">
            Requirements
            {reviewed ? (
              <Badge>Reviewed</Badge>
            ) : (
              <Badge variant="secondary">Draft — review before interviewing</Badge>
            )}
          </CardTitle>
          <p className="text-xs text-muted-foreground">Your 30-second edit pass — everything downstream verifies against this list.</p>
        </div>
        <Button size="sm" onClick={() => save.mutate()} disabled={save.isPending}>
          {save.isPending ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : <Save className="size-3.5" aria-hidden />}
          {save.isPending ? "Saving..." : "Save & mark reviewed"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Skill</TableHead>
                <TableHead>Importance</TableHead>
                <TableHead>Min years</TableHead>
                <TableHead>What would count as evidence</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <Input
                      value={row.skill}
                      onChange={(e) => updateRow(i, { skill: e.target.value, normalized_skill: e.target.value.toLowerCase().trim() })}
                      className="min-w-[10rem]"
                    />
                  </TableCell>
                  <TableCell>
                    <Select value={row.importance} onValueChange={(v) => updateRow(i, { importance: v as RequirementInput["importance"] })}>
                      <SelectTrigger className="w-36">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="must_have">Must-have</SelectItem>
                        <SelectItem value="nice_to_have">Nice-to-have</SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      min={0}
                      step={0.5}
                      value={row.min_years ?? ""}
                      onChange={(e) => updateRow(i, { min_years: e.target.value === "" ? null : Number(e.target.value) })}
                      className="w-20"
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      value={row.evidence_criteria}
                      onChange={(e) => updateRow(i, { evidence_criteria: e.target.value })}
                      className="min-w-[16rem]"
                    />
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon-sm" onClick={() => removeRow(i)} aria-label="Remove requirement">
                      <Trash2 className="size-4 text-muted-foreground transition-colors hover:text-destructive" aria-hidden />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <Button variant="outline" size="sm" onClick={addRow}>
          <Plus className="size-3.5" aria-hidden />
          Add requirement
        </Button>
        {save.isError && <InlineError message={friendlyError(save.error, "Couldn't save the requirements. Please try again.")} />}
      </CardContent>
    </Card>
  );
}

function AddCandidateDialog({ jobId }: { jobId: string }) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [githubLogin, setGithubLogin] = useState("");

  const createCandidate = useMutation({
    mutationFn: () => api.createCandidate(jobId, { name, email: email || undefined, github_login: githubLogin || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["candidates", jobId] });
      setOpen(false);
      setName("");
      setEmail("");
      setGithubLogin("");
    },
  });

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen && createCandidate.isPending) return;
    setOpen(nextOpen);
    if (!nextOpen) createCandidate.reset();
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          <Button size="sm">
            <UserPlus className="size-3.5" aria-hidden />
            Add candidate
          </Button>
        }
      />
      <DialogContent>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createCandidate.mutate();
          }}
        >
          <DialogHeader>
            <DialogTitle>Add candidate</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} disabled={createCandidate.isPending} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email (optional)</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} disabled={createCandidate.isPending} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="github">GitHub username (optional)</Label>
              <Input
                id="github"
                value={githubLogin}
                onChange={(e) => setGithubLogin(e.target.value)}
                placeholder="Only used as supporting evidence"
                disabled={createCandidate.isPending}
              />
            </div>
            {createCandidate.isError && (
              <InlineError message={friendlyError(createCandidate.error, "Couldn't add the candidate. Please try again.")} />
            )}
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createCandidate.isPending || !name.trim()}>
              {createCandidate.isPending && <Loader2 className="size-4 animate-spin" aria-hidden />}
              {createCandidate.isPending ? "Adding..." : "Add candidate"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function CandidateStatusCell({ candidate, jobId }: { candidate: Candidate; jobId: string }) {
  const api = useApi();
  const queryClient = useQueryClient();

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadResume(candidate.id, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["candidates", jobId] }),
  });

  if (candidate.status === "processing" || upload.isPending) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
        <Loader2 className="size-3.5 animate-spin" aria-hidden />
        {upload.isPending ? "Uploading resume..." : "Extracting claims & gathering evidence..."}
      </span>
    );
  }
  if (candidate.status === "ready") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-verdict-verified">
        <CheckCircle2 className="size-3.5 shrink-0" aria-hidden />
        {candidate.status_detail ?? "Ready"}
      </span>
    );
  }
  if (candidate.status === "failed") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-destructive">
        <AlertTriangle className="size-3.5 shrink-0" aria-hidden />
        {candidate.status_detail ?? "Failed"}
      </span>
    );
  }

  return (
    <div className="space-y-1">
      <label className="inline-flex cursor-pointer items-center gap-1.5 text-xs font-medium text-primary transition-colors hover:text-primary/80 hover:underline">
        <Upload className="size-3.5" aria-hidden />
        Upload resume (PDF)
        <input
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) upload.mutate(file);
            e.target.value = "";
          }}
        />
      </label>
      {upload.isError && (
        <p className="text-xs text-destructive">{friendlyError(upload.error, "Upload failed. Please try again.")}</p>
      )}
    </div>
  );
}

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const api = useApi();

  const jobQuery = useQuery({ queryKey: ["jobs", jobId], queryFn: () => api.getJob(jobId) });

  const candidatesQuery = useQuery({
    queryKey: ["candidates", jobId],
    queryFn: () => api.listCandidates(jobId),
    refetchInterval: (query) => (query.state.data?.some((c) => c.status === "processing") ? 2000 : false),
    // Keep polling when the tab is hidden: refetchOnWindowFocus is globally off, so
    // without this a user who tabs away mid-pipeline comes back to a stale "processing"
    // status that never resolves.
    refetchIntervalInBackground: true,
  });

  if (jobQuery.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-24 rounded-md" />
        <Skeleton className="h-9 w-2/3 rounded-md" />
        <Skeleton className="h-64 rounded-xl" />
        <Skeleton className="h-40 rounded-xl" />
      </div>
    );
  }
  if (jobQuery.isError || !jobQuery.data) {
    return (
      <ErrorState
        title="Couldn't load this job"
        message={friendlyError(jobQuery.error)}
        onRetry={() => jobQuery.refetch()}
        retrying={jobQuery.isRefetching}
      />
    );
  }

  const job = jobQuery.data;

  return (
    <div className="space-y-6">
      <div className="fade-up">
        <Link
          href="/jobs"
          className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-3.5 transition-transform duration-200 group-hover:-translate-x-0.5" aria-hidden />
          All jobs
        </Link>
        <h1 className="text-[1.75rem] font-semibold tracking-tight">{job.title}</h1>
        <p className="mt-2 line-clamp-3 max-w-3xl text-sm leading-relaxed whitespace-pre-wrap text-muted-foreground">{job.jd_raw}</p>
      </div>

      <RequirementsEditor jobId={job.id} requirements={job.requirements} reviewed={job.requirements_status === "reviewed"} />

      <Card className="fade-up" style={{ animationDelay: "160ms" }}>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-4">
          <div className="space-y-0.5">
            <CardTitle className="text-base font-semibold">Candidates</CardTitle>
            <p className="text-xs text-muted-foreground">Drop resumes, import a sheet, or share your apply link — the evidence pipeline takes it from there.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ImportSheetDialog jobId={job.id} />
            <ApplyLinkDialog job={job} />
            <AddCandidateDialog jobId={job.id} />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <BulkUploadZone jobId={job.id} />
          {candidatesQuery.isLoading && (
            <div className="space-y-2 py-2">
              <Skeleton className="h-10 rounded-lg" />
              <Skeleton className="h-10 rounded-lg" />
            </div>
          )}
          {candidatesQuery.isError && (
            <ErrorState
              title="Couldn't load candidates"
              message={friendlyError(candidatesQuery.error)}
              onRetry={() => candidatesQuery.refetch()}
              retrying={candidatesQuery.isRefetching}
              className="py-8"
            />
          )}
          {candidatesQuery.data && candidatesQuery.data.length === 0 && (
            <EmptyState
              icon={Users}
              title="No candidates yet"
              body="Drop resumes above, import a sheet from your ATS, or share the public apply link."
              className="border-0 bg-transparent py-8"
            />
          )}
          {candidatesQuery.data && candidatesQuery.data.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Name</TableHead>
                  <TableHead>Pipeline</TableHead>
                  <TableHead className="text-right" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {candidatesQuery.data.map((candidate) => (
                  <TableRow key={candidate.id}>
                    <TableCell className="font-medium">{candidate.name}</TableCell>
                    <TableCell>
                      <CandidateStatusCell candidate={candidate} jobId={job.id} />
                    </TableCell>
                    <TableCell className="text-right">
                      {candidate.status === "ready" && (
                        <Link
                          href={`/jobs/${job.id}/candidates/${candidate.id}`}
                          className="group/link inline-flex items-center gap-0.5 text-sm font-medium text-primary hover:underline"
                        >
                          View evidence
                          <ChevronRight className="size-4 transition-transform duration-200 group-hover/link:translate-x-0.5" aria-hidden />
                        </Link>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
