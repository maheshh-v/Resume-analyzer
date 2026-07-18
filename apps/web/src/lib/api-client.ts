import type {
  ApplyLink,
  BulkUploadResult,
  Candidate,
  CandidateDetail,
  Decision,
  HiringSummary,
  InterviewCreate,
  InterviewState,
  InterviewTranscript,
  Job,
  JobRequirement,
  JobSummary,
  Ledger,
  LedgerVerification,
  LlmCostSummary,
  PublicJob,
  SheetImportResult,
} from "./api-types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// All product endpoints live under /api/v1 (see the backend router prefixing). Callers pass
// bare paths like "/jobs"; request() prepends this once. Non-API fetches (e.g. /health) don't
// go through request() and stay unprefixed.
const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, authToken: string | null, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);
  if (init?.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${API_PREFIX}${path}`, { ...init, headers });
  } catch {
    // fetch() itself threw (server down, network drop, CORS-less 500). Never let the raw
    // "Failed to fetch" TypeError reach the UI — status 0 marks it as a connectivity error.
    throw new ApiError(0, "We couldn't reach the server. Check your connection and try again.");
  }
  if (!response.ok) {
    const detail = await response
      .json()
      .then((body) => body.detail)
      .catch(() => response.statusText);
    throw new ApiError(response.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export type RequirementInput = Omit<JobRequirement, "id" | "ordinal" | "source_span_start" | "source_span_end">;

/** Recruiter-side API, bound to the current Supabase access token. */
export function createApiClient(accessToken: string | null) {
  return {
    listJobs: () => request<JobSummary[]>("/jobs", accessToken),

    createJob: (payload: { title: string; jd_raw: string }) =>
      request<Job>("/jobs", accessToken, { method: "POST", body: JSON.stringify(payload) }),

    getJob: (jobId: string) => request<Job>(`/jobs/${jobId}`, accessToken),

    replaceRequirements: (jobId: string, requirements: RequirementInput[]) =>
      request<Job>(`/jobs/${jobId}/requirements`, accessToken, {
        method: "PUT",
        body: JSON.stringify({ requirements }),
      }),

    deleteJob: (jobId: string) => request<void>(`/jobs/${jobId}`, accessToken, { method: "DELETE" }),

    createCandidate: (jobId: string, payload: { name: string; email?: string; github_login?: string; linkedin_url?: string }) =>
      request<Candidate>(`/jobs/${jobId}/candidates`, accessToken, { method: "POST", body: JSON.stringify(payload) }),

    listCandidates: (jobId: string) => request<Candidate[]>(`/jobs/${jobId}/candidates`, accessToken),

    uploadResume: (candidateId: string, file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return request<Candidate>(`/candidates/${candidateId}/resume`, accessToken, { method: "POST", body: formData });
    },

    bulkUploadResumes: (jobId: string, files: File[]) => {
      const formData = new FormData();
      for (const file of files) formData.append("files", file);
      return request<BulkUploadResult>(`/jobs/${jobId}/candidates/bulk-upload`, accessToken, {
        method: "POST",
        body: formData,
      });
    },

    importCandidateSheet: (jobId: string, file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return request<SheetImportResult>(`/jobs/${jobId}/candidates/import`, accessToken, {
        method: "POST",
        body: formData,
      });
    },

    createApplyLink: (jobId: string) => request<ApplyLink>(`/jobs/${jobId}/apply-link`, accessToken, { method: "POST" }),

    disableApplyLink: (jobId: string) => request<void>(`/jobs/${jobId}/apply-link`, accessToken, { method: "DELETE" }),

    getCandidateDetail: (candidateId: string) => request<CandidateDetail>(`/candidates/${candidateId}`, accessToken),

    createInterview: (candidateId: string) =>
      request<InterviewCreate>(`/candidates/${candidateId}/interviews`, accessToken, { method: "POST" }),

    getTranscript: (candidateId: string, interviewId: string) =>
      request<InterviewTranscript>(`/candidates/${candidateId}/interviews/${interviewId}/transcript`, accessToken),

    getReport: (candidateId: string) => request<HiringSummary>(`/candidates/${candidateId}/report`, accessToken),

    recordDecision: (candidateId: string, payload: { verdict: string; rationale: string }) =>
      request<Decision>(`/candidates/${candidateId}/decision`, accessToken, {
        method: "POST",
        body: JSON.stringify(payload),
      }),

    getLlmCosts: (candidateId: string) =>
      request<LlmCostSummary>(`/candidates/${candidateId}/llm-costs`, accessToken),

    getLedger: (candidateId: string) => request<Ledger>(`/candidates/${candidateId}/ledger`, accessToken),

    verifyLedger: (candidateId: string) =>
      request<LedgerVerification>(`/candidates/${candidateId}/ledger/verify`, accessToken),
  };
}

/** The public apply page is unauthenticated by design — a tokenized link a recruiter shares
 * anywhere (job post, email, careers page), mirroring the interview portal pattern. */
export const publicApplyApi = {
  getJob: (applyToken: string) => request<PublicJob>(`/apply/${applyToken}`, null),

  submitApplication: (
    applyToken: string,
    payload: { name: string; email: string; github_login?: string; linkedin_url?: string; file: File },
  ) => {
    const formData = new FormData();
    formData.append("name", payload.name);
    formData.append("email", payload.email);
    if (payload.github_login) formData.append("github_login", payload.github_login);
    if (payload.linkedin_url) formData.append("linkedin_url", payload.linkedin_url);
    formData.append("file", payload.file);
    return request<{ status: string }>(`/apply/${applyToken}`, null, { method: "POST", body: formData });
  },
};

/** The candidate-facing interview portal is unauthenticated by design — a tokenized link,
 * not a Supabase session. See docs/ARCHITECTURE.md. */
export const publicInterviewApi = {
  getState: (interviewToken: string) => request<InterviewState>(`/interview/${interviewToken}`, null),

  submitAnswer: (
    interviewToken: string,
    questionId: string,
    payload: {
      answer_text: string;
      time_to_first_keystroke_ms?: number;
      total_time_ms?: number;
      paste_event_count?: number;
      revision_count?: number;
    },
  ) =>
    request<InterviewState>(`/interview/${interviewToken}/questions/${questionId}/answer`, null, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
