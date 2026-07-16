// Mirrors apps/api/app/schemas/*.py. Kept hand-written rather than generated for the MVP —
// if the backend schema drifts, the type-checker here won't catch it, but this avoids an
// OpenAPI-codegen build step for a project this size. Revisit if the schema churns a lot.

export interface JobRequirement {
  id: string;
  ordinal: number;
  skill: string;
  normalized_skill: string;
  category: string;
  importance: "must_have" | "nice_to_have";
  min_years: number | null;
  evidence_criteria: string;
  source_span_start: number | null;
  source_span_end: number | null;
}

export interface Job {
  id: string;
  title: string;
  jd_raw: string;
  requirements_status: "draft" | "reviewed";
  created_at: string;
  requirements: JobRequirement[];
}

export interface JobSummary {
  id: string;
  title: string;
  requirements_status: "draft" | "reviewed";
  created_at: string;
  candidate_count: number;
}

export interface Candidate {
  id: string;
  job_id: string;
  name: string;
  email: string | null;
  github_login: string | null;
  linkedin_url: string | null;
  status: "pending" | "processing" | "ready" | "failed";
  status_detail: string | null;
  created_at: string;
}

export interface Claim {
  id: string;
  claim_type: "skill" | "employment" | "education" | "project" | "credential";
  claim_text: string;
  normalized_skill: string | null;
  asserted_years: number | null;
  asserted_start: string | null;
  asserted_end: string | null;
  asserted_org: string | null;
  source_span_start: number;
  source_span_end: number;
}

export type EvidenceVerdict = "verified" | "partial" | "unverified" | "contradicted";

export interface Evidence {
  id: string;
  claim_id: string;
  source_type: "consistency" | "github" | "interview";
  verdict: EvidenceVerdict;
  summary: string;
  artifact_url: string | null;
  artifact_snippet: string | null;
}

export interface MatchRow {
  requirement_id: string;
  skill: string;
  importance: string;
  status: "matched" | "partial" | "gap";
  matching_claim_ids: string[];
  note: string;
}

export interface CandidateDetail {
  candidate: Candidate;
  claims: Claim[];
  evidence: Evidence[];
  matches: MatchRow[];
  extraction_stats: Record<string, number>;
}

export interface InterviewCreate {
  id: string;
  token: string;
  status: string;
  expires_at: string;
  interview_url_path: string;
}

export interface InterviewQuestionPublic {
  id: string;
  ordinal: number;
  question_text: string;
}

export interface InterviewState {
  status: "pending" | "in_progress" | "submitted" | "expired";
  current_question: InterviewQuestionPublic | null;
  questions_answered: number;
  is_complete: boolean;
}

export interface InterviewQuestionRecruiter {
  id: string;
  ordinal: number;
  depth: number;
  targets_claim_id: string;
  question_text: string;
  grounding_artifact_url: string | null;
  rubric: { must_mention: string[]; bluffer_tells: string[] };
  rationale: string;
}

export interface InterviewAnswerRecruiter {
  question_id: string;
  answer_text: string;
  specificity_verdict: "strong" | "weak";
  specificity_notes: string;
  review_flags: string[];
}

export interface InterviewTranscript {
  interview_id: string;
  status: string;
  questions: InterviewQuestionRecruiter[];
  answers: InterviewAnswerRecruiter[];
}

export interface MatrixRow {
  requirement_id: string;
  skill: string;
  importance: string;
  match_status: string;
  claim_texts: string[];
  best_verdict: EvidenceVerdict;
  evidence_summaries: string[];
  evidence_urls: string[];
}

export interface QAExchange {
  depth: number;
  question_text: string;
  rationale: string;
  answer_text: string | null;
  specificity_verdict: "strong" | "weak" | null;
  specificity_notes: string | null;
  review_flags: string[];
}

export interface HiringSummary {
  evidence_coverage_count: number;
  evidence_coverage_total: number;
  evidence_coverage_note: string;
  conflicts: string[];
  matrix: MatrixRow[];
  verified_skills: MatrixRow[];
  needs_manual_verification: MatrixRow[];
  technical_strengths: string[];
  weak_areas: string[];
  suggested_followups: string[];
  transcript: QAExchange[];
}

export interface Decision {
  id: string;
  candidate_id: string;
  verdict: "advance" | "hold" | "decline";
  rationale: string;
  decided_by_user_id: string;
}
