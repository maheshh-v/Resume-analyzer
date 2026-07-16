"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
import { useApi } from "@/hooks/use-api";
import type { RequirementInput } from "@/lib/api-client";
import type { Candidate } from "@/lib/api-types";

function statusVariant(status: Candidate["status"]) {
  switch (status) {
    case "ready":
      return "default" as const;
    case "failed":
      return "destructive" as const;
    default:
      return "secondary" as const;
  }
}

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
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Requirements {reviewed ? <Badge className="ml-2">Reviewed</Badge> : <Badge variant="secondary" className="ml-2">Draft — review before interviewing</Badge>}</CardTitle>
        <Button size="sm" onClick={() => save.mutate()} disabled={save.isPending}>
          {save.isPending ? "Saving..." : "Save & mark reviewed"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Skill</TableHead>
              <TableHead>Importance</TableHead>
              <TableHead>Min years</TableHead>
              <TableHead>Evidence criteria</TableHead>
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
                  <Button variant="ghost" size="sm" onClick={() => removeRow(i)}>
                    Remove
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <Button variant="outline" size="sm" onClick={addRow}>
          Add requirement
        </Button>
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

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm">Add candidate</Button>} />
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
              <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email (optional)</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="github">GitHub username (optional)</Label>
              <Input id="github" value={githubLogin} onChange={(e) => setGithubLogin(e.target.value)} placeholder="Only used as supporting evidence" />
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createCandidate.isPending}>
              {createCandidate.isPending ? "Adding..." : "Add candidate"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ResumeUploadCell({ candidate, jobId }: { candidate: Candidate; jobId: string }) {
  const api = useApi();
  const queryClient = useQueryClient();

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadResume(candidate.id, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["candidates", jobId] }),
  });

  if (candidate.status === "processing") {
    return <span className="text-xs text-muted-foreground">Processing...</span>;
  }
  if (candidate.status === "ready") {
    return <span className="text-xs text-muted-foreground">{candidate.status_detail}</span>;
  }
  if (candidate.status === "failed") {
    return <span className="text-xs text-destructive">{candidate.status_detail ?? "Failed"}</span>;
  }

  return (
    <label className="cursor-pointer text-xs text-primary underline">
      Upload resume
      <input
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) upload.mutate(file);
        }}
      />
    </label>
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
  });

  if (jobQuery.isLoading) {
    return <Skeleton className="h-64 rounded-lg" />;
  }
  if (jobQuery.isError || !jobQuery.data) {
    return <p className="text-sm text-destructive">Failed to load job.</p>;
  }

  const job = jobQuery.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{job.title}</h1>
        <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground line-clamp-3">{job.jd_raw}</p>
      </div>

      <RequirementsEditor jobId={job.id} requirements={job.requirements} reviewed={job.requirements_status === "reviewed"} />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Candidates</CardTitle>
          <AddCandidateDialog jobId={job.id} />
        </CardHeader>
        <CardContent>
          {candidatesQuery.isLoading && <Skeleton className="h-24 rounded" />}
          {candidatesQuery.data && candidatesQuery.data.length === 0 && (
            <p className="text-sm text-muted-foreground">No candidates yet.</p>
          )}
          {candidatesQuery.data && candidatesQuery.data.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Resume</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {candidatesQuery.data.map((candidate) => (
                  <TableRow key={candidate.id}>
                    <TableCell className="font-medium">{candidate.name}</TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(candidate.status)}>{candidate.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <ResumeUploadCell candidate={candidate} jobId={job.id} />
                    </TableCell>
                    <TableCell className="text-right">
                      {candidate.status === "ready" && (
                        <Link href={`/jobs/${job.id}/candidates/${candidate.id}`} className="text-sm text-primary underline">
                          View details
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
