"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, FileSpreadsheet, Link2, Loader2, RotateCw, Trash2, Upload } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { InlineError } from "@/components/states";
import { useApi } from "@/hooks/use-api";
import type { BulkUploadResult, Job, SheetImportResult } from "@/lib/api-types";
import { friendlyError } from "@/lib/errors";
import { cn } from "@/lib/utils";

/** Bulk intake surfaces for the job page: multi-PDF dropzone, sheet import, and the
 * public apply link. All three land candidates in the same verification pipeline as the
 * one-at-a-time dialog — these are just the ways candidates arrive in volume. */

// --- Multi-PDF dropzone ----------------------------------------------------------------

export function BulkUploadZone({ jobId }: { jobId: string }) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [dragActive, setDragActive] = useState(false);
  const [lastResult, setLastResult] = useState<BulkUploadResult | null>(null);

  const upload = useMutation({
    mutationFn: (files: File[]) => api.bulkUploadResumes(jobId, files),
    onSuccess: (result) => {
      setLastResult(result);
      queryClient.invalidateQueries({ queryKey: ["candidates", jobId] });
    },
  });

  function handleFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    setLastResult(null);
    upload.mutate(Array.from(fileList));
  }

  return (
    <div className="space-y-2">
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center gap-1.5 rounded-xl border border-dashed px-6 py-7 text-center transition-colors",
          dragActive ? "border-primary bg-primary/[0.06]" : "border-border bg-card/50 hover:border-primary/50",
        )}
      >
        {upload.isPending ? (
          <Loader2 className="size-5 animate-spin text-primary" aria-hidden />
        ) : (
          <Upload className="size-5 text-primary/70" aria-hidden />
        )}
        <span className="text-sm font-medium">
          {upload.isPending ? "Uploading resumes..." : "Drop resumes here, or click to choose"}
        </span>
        <span className="text-xs text-muted-foreground">
          One PDF per candidate — names come from the filenames. Up to 20 at a time.
        </span>
        <input
          type="file"
          accept="application/pdf"
          multiple
          className="hidden"
          disabled={upload.isPending}
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </label>
      {upload.isError && <InlineError message={friendlyError(upload.error, "Bulk upload failed. Please try again.")} />}
      {lastResult && (
        <div className="space-y-1 text-xs text-muted-foreground">
          <p>
            {lastResult.created.length} candidate{lastResult.created.length === 1 ? "" : "s"} added
            {lastResult.errors.length > 0 && `, ${lastResult.errors.length} skipped`}.
          </p>
          {lastResult.errors.map((error) => (
            <p key={error} className="text-destructive">
              {error}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

// --- CSV / XLSX sheet import -----------------------------------------------------------

const CSV_TEMPLATE =
  "name,email,github,linkedin,resume_url\n" +
  "Jane Doe,jane@example.com,janedoe,https://linkedin.com/in/janedoe,https://example.com/jane-resume.pdf\n";

function downloadTemplate() {
  const blob = new Blob([CSV_TEMPLATE], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "candidates-template.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ImportSheetDialog({ jobId }: { jobId: string }) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [result, setResult] = useState<SheetImportResult | null>(null);

  const importSheet = useMutation({
    mutationFn: (file: File) => api.importCandidateSheet(jobId, file),
    onSuccess: (imported) => {
      setResult(imported);
      queryClient.invalidateQueries({ queryKey: ["candidates", jobId] });
    },
  });

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen && importSheet.isPending) return;
    setOpen(nextOpen);
    if (!nextOpen) {
      importSheet.reset();
      setResult(null);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm">
            <FileSpreadsheet className="size-3.5" aria-hidden />
            Import sheet
          </Button>
        }
      />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import candidates from a sheet</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Upload a .csv or .xlsx export — from your ATS, a Google Sheet, anywhere. Columns: name (required), email,
            github, linkedin, resume_url. Rows with a resume URL start verifying immediately.
          </p>
          <label
            className={cn(
              "flex cursor-pointer flex-col items-center gap-1.5 rounded-xl border border-dashed border-border bg-card/50 px-6 py-7 text-center transition-colors hover:border-primary/50",
              importSheet.isPending && "pointer-events-none opacity-60",
            )}
          >
            {importSheet.isPending ? (
              <Loader2 className="size-5 animate-spin text-primary" aria-hidden />
            ) : (
              <FileSpreadsheet className="size-5 text-primary/70" aria-hidden />
            )}
            <span className="text-sm font-medium">{importSheet.isPending ? "Importing..." : "Choose a .csv or .xlsx file"}</span>
            <input
              type="file"
              accept=".csv,.xlsx"
              className="hidden"
              disabled={importSheet.isPending}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  setResult(null);
                  importSheet.mutate(file);
                }
                e.target.value = "";
              }}
            />
          </label>
          <button type="button" onClick={downloadTemplate} className="text-xs font-medium text-primary hover:underline">
            Download the CSV template
          </button>
          {importSheet.isError && (
            <InlineError message={friendlyError(importSheet.error, "Couldn't import that sheet. Check the format and try again.")} />
          )}
          {result && (
            <div className="space-y-1 text-sm">
              <p>
                {result.created.length} candidate{result.created.length === 1 ? "" : "s"} imported
                {result.fetching_count > 0 && ` — fetching ${result.fetching_count} resume${result.fetching_count === 1 ? "" : "s"} now`}
                .
              </p>
              {result.errors.map((error) => (
                <p key={error} className="text-xs text-destructive">
                  {error}
                </p>
              ))}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={importSheet.isPending}>
            {result ? "Done" : "Cancel"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// --- Public apply link -----------------------------------------------------------------

export function ApplyLinkDialog({ job }: { job: Job }) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const invalidateJob = () => queryClient.invalidateQueries({ queryKey: ["jobs", job.id] });
  const create = useMutation({ mutationFn: () => api.createApplyLink(job.id), onSuccess: invalidateJob });
  const disable = useMutation({ mutationFn: () => api.disableApplyLink(job.id), onSuccess: invalidateJob });

  const applyUrl =
    job.apply_token && typeof window !== "undefined" ? `${window.location.origin}/apply/${job.apply_token}` : null;
  const busy = create.isPending || disable.isPending;

  async function copyLink() {
    if (!applyUrl) return;
    await navigator.clipboard.writeText(applyUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm">
            <Link2 className="size-3.5" aria-hidden />
            Apply link
          </Button>
        }
      />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Public apply link</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <p className="text-sm leading-relaxed text-muted-foreground">
            Share this link in your job post, careers page, or outreach. Candidates apply with their own details and
            resume — verification starts the moment they submit, with every step recorded in the evidence ledger. No
            data entry on your side.
          </p>
          {applyUrl ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <code className="min-w-0 flex-1 truncate rounded-lg border border-border bg-muted/50 px-3 py-2 text-xs">
                  {applyUrl}
                </code>
                <Button variant="outline" size="sm" onClick={copyLink} aria-label="Copy apply link">
                  {copied ? <Check className="size-3.5 text-verdict-verified" aria-hidden /> : <Copy className="size-3.5" aria-hidden />}
                  {copied ? "Copied" : "Copy"}
                </Button>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={() => create.mutate()} disabled={busy}>
                  {create.isPending ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : <RotateCw className="size-3.5" aria-hidden />}
                  Rotate link
                </Button>
                <Button variant="outline" size="sm" onClick={() => disable.mutate()} disabled={busy}>
                  {disable.isPending ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : <Trash2 className="size-3.5" aria-hidden />}
                  Disable link
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Rotating or disabling immediately invalidates every previously shared copy.
              </p>
            </div>
          ) : (
            <Button onClick={() => create.mutate()} disabled={busy}>
              {create.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Link2 className="size-4" aria-hidden />}
              {create.isPending ? "Creating..." : "Create apply link"}
            </Button>
          )}
          {(create.isError || disable.isError) && (
            <InlineError message={friendlyError(create.error ?? disable.error, "Couldn't update the apply link. Please try again.")} />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
