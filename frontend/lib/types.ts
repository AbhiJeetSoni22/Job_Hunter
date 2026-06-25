// ── API envelope ──────────────────────────────────────────────────────────────
// Every backend response is { data: T | null, error: ApiError | null }

export interface ApiError {
  code: string;
  message: string;
}

export interface ApiResponse<T> {
  data: T | null;
  error: ApiError | null;
}

// ── Resume ────────────────────────────────────────────────────────────────────

export interface Resume {
  id: string;
  filename: string;
  skills: string[];
  uploaded_at: string; // ISO 8601 UTC
}

export interface ResumeUploadResponse extends Resume {
  page_count: number;
  char_count: number;
}

// ── Jobs ──────────────────────────────────────────────────────────────────────

export type JobStatus = "saved" | "applied" | "interview" | "offer" | "rejected";
export type JobSource = "remoteok" | "yc_jobs";
export type SortBy = "created_at" | "posted_at" | "match_score";

/** Returned by GET /api/jobs — no description, notes, or match_summary */
export interface JobListItem {
  id: string;
  title: string;
  company: string;
  company_url: string | null;
  url: string;
  source: JobSource;
  location: string | null;
  status: JobStatus;
  match_score: number | null;
  needs_rescore: boolean;
  posted_at: string | null;
  created_at: string;
  updated_at: string;
}

/** Returned by GET /api/jobs/:id — full record */
export interface Job extends JobListItem {
  description: string;
  notes: string | null;
  missing_skills: string[] | null;
  match_summary: string | null;
  matched_at: string | null;
  resume_uploaded_at: string | null;
}

export interface PaginatedJobList {
  jobs: JobListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobListParams {
  page?: number;
  page_size?: number;
  sort_by?: SortBy;
  order?: "asc" | "desc";
  status?: JobStatus;
  source?: JobSource;
  scored?: boolean;
}

export interface JobUpdateRequest {
  status?: JobStatus;
  notes?: string;
}

export interface JobUpdateResponse {
  id: string;
  status: JobStatus;
  notes: string | null;
}

// ── Scoring ───────────────────────────────────────────────────────────────────

export interface ScoreResponse {
  match_score: number;
  missing_skills: string[];
  match_summary: string;
  matched_at: string;
  cached: boolean;
  needs_rescore: boolean;
}

// ── Scraper ───────────────────────────────────────────────────────────────────

export interface ScraperRun {
  source: JobSource;
  jobs_found: number;
  jobs_new: number;
  error: string | null;
  started_at: string;
  completed_at: string;
}

export interface ScraperRunResult {
  runs: ScraperRun[];
  total_new: number;
}

// ── Health ────────────────────────────────────────────────────────────────────

export interface HealthStatus {
  status: "ok" | "degraded";
  database: "connected" | "unreachable";
}
