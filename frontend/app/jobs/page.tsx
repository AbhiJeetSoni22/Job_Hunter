"use client";

import { useState, useEffect, useCallback, useTransition } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { JobList } from "@/components/jobs/JobList";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/ErrorState";
import { JobCardSkeleton } from "@/components/ui/Skeleton";
import { ToastContainer, useToast } from "@/components/ui/Toast";
import { getJobs, getResume, ApiClientError } from "@/lib/api";
import type {
  JobListItem,
  JobListParams,
  JobStatus,
  JobSource,
  SortBy,
} from "@/lib/types";

// ── Filter state ───────────────────────────────────────────────────────────────

interface Filters {
  status: JobStatus | "";
  source: JobSource | "";
  scored: "" | "true" | "false";
  sort_by: SortBy;
  order: "asc" | "desc";
  page: number;
}

const DEFAULT_FILTERS: Filters = {
  status: "",
  source: "",
  scored: "",
  sort_by: "created_at",
  order: "desc",
  page: 1,
};

const PAGE_SIZE = 20;

// ── Select helper ──────────────────────────────────────────────────────────────

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label
      className="flex flex-col gap-1"
      style={{ fontSize: "0.78rem", color: "var(--color-muted)" }}
    >
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "0.375rem",
          color: "var(--color-text)",
          padding: "0.3rem 0.5rem",
          fontSize: "0.8rem",
          cursor: "pointer",
        }}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function JobsPage() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const { toasts, addToast, dismiss } = useToast();
  // Resume presence — fetched once, independent of job filters. Reused to
  // gate match-score visibility, consistent with the Dashboard's rule.
  const [hasResume, setHasResume] = useState<boolean | null>(null);

  useEffect(() => {
    getResume()
      .then((r) => setHasResume(r !== null))
      .catch(() => setHasResume(null));
  }, []);

  const load = useCallback(async (f: Filters) => {
    setLoading(true);
    setError(null);
    try {
      const params: JobListParams = {
        page: f.page,
        page_size: PAGE_SIZE,
        sort_by: f.sort_by,
        order: f.order,
      };
      if (f.status) params.status = f.status as JobStatus;
      if (f.source) params.source = f.source as JobSource;
      if (f.scored !== "") params.scored = f.scored === "true";

      const result = await getJobs(params);
      setJobs(result.jobs);
      setTotal(result.total);
    } catch (err) {
      setError(
        err instanceof ApiClientError ? err.message : "Failed to load jobs.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(filters);
  }, [filters, load]);

  function update(patch: Partial<Filters>) {
    startTransition(() => {
      setFilters((prev) => ({ ...prev, ...patch, page: patch.page ?? 1 }));
    });
  }

  // Keep the visible list in sync after an inline status change on a card,
  // without a full refetch. If the new status no longer matches the active
  // status filter, drop the job from view.
  function handleStatusChanged(jobId: string, newStatus: JobStatus) {
    setJobs((prev) => {
      if (filters.status && filters.status !== newStatus) {
        setTotal((t) => Math.max(0, t - 1));
        return prev.filter((j) => j.id !== jobId);
      }
      return prev.map((j) =>
        j.id === jobId ? { ...j, status: newStatus } : j,
      );
    });
    addToast(`Status updated to "${newStatus}".`, "success");
  }

  function handleStatusError(message: string) {
    addToast(message, "error");
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <PageHeader
        title="Jobs"
        subtitle={
          loading
            ? "Loading…"
            : `${total} internship${total !== 1 ? "s" : ""} in database`
        }
      />

      {/* ── Resume-required banner ──────────────────────────────────── */}
      {hasResume === false && (
        <div
          className="mb-4 px-4 py-2 rounded-lg text-sm"
          style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            color: "var(--color-subtle)",
          }}
        >
          Upload a resume to view personalized AI match scores.{" "}
          <Link
            href="/resume"
            style={{ color: "var(--color-accent)", fontWeight: 600 }}
          >
            Upload Resume
          </Link>
        </div>
      )}

      {/* ── Filter bar ───────────────────────────────────────────────── */}
      <div
        className="flex flex-wrap gap-4 mb-5 p-4 rounded-lg"
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
        }}
      >
        <FilterSelect
          label="Status"
          value={filters.status}
          onChange={(v) => update({ status: v as Filters["status"] })}
          options={[
            { value: "", label: "All statuses" },
            { value: "saved", label: "Saved" },
            { value: "applied", label: "Applied" },
            { value: "interview", label: "Interview" },
            { value: "offer", label: "Offer" },
            { value: "rejected", label: "Rejected" },
          ]}
        />
        <FilterSelect
          label="Source"
          value={filters.source}
          onChange={(v) => update({ source: v as Filters["source"] })}
          options={[
            { value: "", label: "All sources" },
            { value: "remoteok", label: "RemoteOK" },
            { value: "yc_jobs", label: "YC Jobs" },
          ]}
        />
        <FilterSelect
          label="Scored"
          value={filters.scored}
          onChange={(v) => update({ scored: v as Filters["scored"] })}
          options={[
            { value: "", label: "All" },
            { value: "true", label: "Scored" },
            { value: "false", label: "Unscored" },
          ]}
        />
        <FilterSelect
          label="Sort by"
          value={filters.sort_by}
          onChange={(v) => update({ sort_by: v as SortBy })}
          options={[
            { value: "created_at", label: "Date added" },
            { value: "posted_at", label: "Posted date" },
            { value: "match_score", label: "Match score" },
          ]}
        />
        <FilterSelect
          label="Order"
          value={filters.order}
          onChange={(v) => update({ order: v as "asc" | "desc" })}
          options={[
            { value: "desc", label: "Newest first" },
            { value: "asc", label: "Oldest first" },
          ]}
        />
        <div className="flex items-end">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => update(DEFAULT_FILTERS)}
            disabled={loading}
          >
            Reset
          </Button>
        </div>
      </div>

      {/* ── Content ──────────────────────────────────────────────────── */}
      {loading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <JobCardSkeleton key={i} />
          ))}
        </div>
      ) : error ? (
        <ErrorState message={error} />
      ) : (
        <>
          <JobList
            jobs={jobs}
            onStatusChanged={handleStatusChanged}
            onStatusError={handleStatusError}
            hasResume={hasResume ?? true}
          />

          {/* ── Pagination ─────────────────────────────────────────── */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 mt-6">
              <Button
                variant="secondary"
                size="sm"
                disabled={filters.page <= 1 || isPending}
                onClick={() => update({ page: filters.page - 1 })}
              >
                ← Prev
              </Button>
              <span style={{ fontSize: "0.8rem", color: "var(--color-muted)" }}>
                Page {filters.page} of {totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={filters.page >= totalPages || isPending}
                onClick={() => update({ page: filters.page + 1 })}
              >
                Next →
              </Button>
            </div>
          )}
        </>
      )}

      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
