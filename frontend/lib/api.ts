/**
 * lib/api.ts — centralised backend client
 *
 * All fetch calls go here. Components never call fetch directly.
 *
 * Base URL resolution:
 *   - Browser:     relative /api/* → proxied to localhost:8000 by next.config.ts
 *   - Server-side: API_BASE_URL env var (server-only, not exposed to browser)
 *                  falls back to http://localhost:8000
 *
 * Error contract:
 *   - Network / timeout      → throws ApiClientError("NETWORK_ERROR")
 *   - Non-JSON response      → throws ApiClientError("INVALID_RESPONSE")
 *   - Backend error envelope → throws ApiClientError from error.code / error.message
 *   - Non-2xx with no body   → throws ApiClientError("UNKNOWN_ERROR")
 */

import type {
  ApiResponse,
  HealthStatus,
  Job,
  JobListParams,
  JobUpdateRequest,
  JobUpdateResponse,
  PaginatedJobList,
  Resume,
  ResumeUploadResponse,
  ScoreResponse,
  ScraperRun,
  ScraperRunResult,
} from "./types";

// ── Client error class ────────────────────────────────────────────────────────

export class ApiClientError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

// ── Config ────────────────────────────────────────────────────────────────────

const REQUEST_TIMEOUT_MS = 120_000;

function baseUrl(): string {
  if (typeof window === "undefined") {
    // Server-side: use API_BASE_URL (not exposed to browser, safe for internal URLs)
    return process.env.API_BASE_URL ?? "http://localhost:8000";
  }
  // Browser: empty string → Next.js rewrite proxy handles /api/* → backend
  return "";
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${baseUrl()}${path}`;

  // Build headers — never set Content-Type for FormData;
  // the browser must set it with the correct multipart boundary.
  const isFormData = init?.body instanceof FormData;
  const headers: HeadersInit = isFormData
    ? { ...(init?.headers as Record<string, string>) }
    : { "Content-Type": "application/json", ...(init?.headers as Record<string, string>) };

  // 15-second timeout via AbortController
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiClientError("TIMEOUT", "Request timed out after 15 seconds.");
    }
    throw new ApiClientError("NETWORK_ERROR", "Could not reach the server.");
  } finally {
    clearTimeout(timeoutId);
  }

  // 204 No Content (DELETE /api/resume has no body)
  if (res.status === 204) {
    return undefined as T;
  }

  // Guard against non-JSON responses (nginx error pages, proxy errors, etc.)
  const contentType = res.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    throw new ApiClientError(
      "INVALID_RESPONSE",
      `Expected JSON but got "${contentType}" (status ${res.status}).`,
    );
  }

  const json: ApiResponse<T> = await res.json();

  if (!res.ok || json.error) {
    throw new ApiClientError(
      json.error?.code ?? "UNKNOWN_ERROR",
      json.error?.message ?? `Request failed (${res.status}).`,
    );
  }

  return json.data as T;
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>("/api/health");
}

// ── Resume ────────────────────────────────────────────────────────────────────

export async function getResume(): Promise<Resume | null> {
  try {
    return await apiFetch<Resume>("/api/resume");
  } catch (err) {
    if (err instanceof ApiClientError && err.code === "NO_RESUME") return null;
    throw err;
  }
}

export async function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<ResumeUploadResponse>("/api/resume", { method: "POST", body: form });
}

export async function deleteResume(): Promise<void> {
  return apiFetch<void>("/api/resume", { method: "DELETE" });
}

// ── Jobs ──────────────────────────────────────────────────────────────────────

export async function getJobs(params: JobListParams = {}): Promise<PaginatedJobList> {
  const qs = new URLSearchParams();
  if (params.page !== undefined)      qs.set("page",      String(params.page));
  if (params.page_size !== undefined) qs.set("page_size", String(params.page_size));
  if (params.sort_by)                 qs.set("sort_by",   params.sort_by);
  if (params.order)                   qs.set("order",     params.order);
  if (params.status)                  qs.set("status",    params.status);
  if (params.source)                  qs.set("source",    params.source);
  if (params.scored !== undefined)    qs.set("scored",    String(params.scored));

  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<PaginatedJobList>(`/api/jobs${query}`);
}

export async function getJob(id: string): Promise<Job> {
  return apiFetch<Job>(`/api/jobs/${id}`);
}

export async function updateJob(id: string, body: JobUpdateRequest): Promise<JobUpdateResponse> {
  return apiFetch<JobUpdateResponse>(`/api/jobs/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function scoreJob(id: string): Promise<ScoreResponse> {
  return apiFetch<ScoreResponse>(`/api/jobs/${id}/score`, { method: "POST" });
}

export async function deleteJob(id: string): Promise<void> {
  return apiFetch<void>(`/api/jobs/${id}`, { method: "DELETE" });
}

// ── Scraper ───────────────────────────────────────────────────────────────────

export async function runScraper(): Promise<ScraperRunResult> {
  return apiFetch<ScraperRunResult>("/api/scraper/run", { method: "POST" });
}

export async function getScraperStatus(): Promise<ScraperRun[]> {
  return apiFetch<ScraperRun[]>("/api/scraper/status");
}