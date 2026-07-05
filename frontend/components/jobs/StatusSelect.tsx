"use client";

import { useState } from "react";
import { updateJob, ApiClientError } from "@/lib/api";
import type { JobStatus } from "@/lib/types";

interface StatusSelectProps {
  jobId: string;
  status: JobStatus;
  /** Called after a successful save so parent list state can stay in sync. */
  onChanged?: (jobId: string, newStatus: JobStatus) => void;
  onError?: (message: string) => void;
}

const CONFIG: Record<JobStatus, { label: string; bg: string; text: string }> = {
  saved: {
    label: "Saved",
    bg: "rgba(75,83,99,0.25)",
    text: "var(--color-subtle)",
  },
  applied: {
    label: "Applied",
    bg: "rgba(56,189,248,0.15)",
    text: "var(--color-sky)",
  },
  interview: {
    label: "Interview",
    bg: "rgba(99,102,241,0.2)",
    text: "var(--color-accent-h)",
  },
  offer: {
    label: "Offer",
    bg: "rgba(34,197,94,0.15)",
    text: "var(--color-green)",
  },
  rejected: {
    label: "Rejected",
    bg: "rgba(239,68,68,0.15)",
    text: "var(--color-red)",
  },
};

const OPTIONS: JobStatus[] = [
  "saved",
  "applied",
  "interview",
  "offer",
  "rejected",
];

/**
 * Compact badge-styled status dropdown for use inside JobCard.
 * Stops click/mousedown propagation so it works inside the card's
 * outer <Link> without triggering navigation.
 */
export function StatusSelect({
  jobId,
  status,
  onChanged,
  onError,
}: StatusSelectProps) {
  const [current, setCurrent] = useState<JobStatus>(status);
  const [saving, setSaving] = useState(false);
  const { bg, text } = CONFIG[current] ?? CONFIG.saved;

  async function handleChange(newStatus: JobStatus) {
    if (saving || newStatus === current) return;
    const prev = current;
    setCurrent(newStatus); // optimistic
    setSaving(true);
    try {
      await updateJob(jobId, { status: newStatus });
      onChanged?.(jobId, newStatus);
    } catch (err) {
      setCurrent(prev); // rollback
      onError?.(
        err instanceof ApiClientError ? err.message : "Status update failed.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <select
      value={current}
      disabled={saving}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
      }}
      onMouseDown={(e) => e.stopPropagation()}
      onChange={(e) => handleChange(e.target.value as JobStatus)}
      aria-label="Job status"
      style={{
        background: bg,
        color: text,
        fontSize: "0.7rem",
        fontWeight: 600,
        letterSpacing: "0.03em",
        textTransform: "uppercase",
        border: "none",
        borderRadius: "9999px",
        padding: "0.15rem 0.5rem",
        cursor: saving ? "not-allowed" : "pointer",
        opacity: saving ? 0.6 : 1,
        appearance: "none",
        WebkitAppearance: "none",
      }}
    >
      {OPTIONS.map((s) => (
        <option
          key={s}
          value={s}
          style={{
            background: "var(--color-surface)",
            color: "var(--color-text)",
          }}
        >
          {CONFIG[s].label}
        </option>
      ))}
    </select>
  );
}
