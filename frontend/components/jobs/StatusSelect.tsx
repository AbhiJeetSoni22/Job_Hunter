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

const CONFIG: Record<JobStatus, { label: string; bg: string; text: string; border: string }> = {
  saved: {
    label: "Saved",
    bg: "rgba(255, 255, 255, 0.06)",
    text: "var(--color-subtle)",
    border: "rgba(255, 255, 255, 0.14)",
  },
  applied: {
    label: "Applied",
    bg: "rgba(56, 189, 248, 0.12)",
    text: "var(--color-sky)",
    border: "rgba(56, 189, 248, 0.28)",
  },
  interview: {
    label: "Interview",
    bg: "var(--color-gold-subtle)",
    text: "var(--color-gold)",
    border: "var(--color-gold-border)",
  },
  offer: {
    label: "Offer",
    bg: "rgba(34, 197, 94, 0.12)",
    text: "var(--color-green)",
    border: "rgba(34, 197, 94, 0.28)",
  },
  rejected: {
    label: "Rejected",
    bg: "rgba(239, 68, 68, 0.12)",
    text: "var(--color-red)",
    border: "rgba(239, 68, 68, 0.28)",
  },
};

const OPTIONS: JobStatus[] = [
  "saved",
  "applied",
  "interview",
  "offer",
  "rejected",
];

export function StatusSelect({
  jobId,
  status,
  onChanged,
  onError,
}: StatusSelectProps) {
  const [current, setCurrent] = useState<JobStatus>(status);
  const [saving, setSaving] = useState(false);
  const { bg, text, border } = CONFIG[current] ?? CONFIG.saved;

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
        border: `1px solid ${border}`,
        fontSize: "0.6875rem",
        fontWeight: 600,
        letterSpacing: "0.03em",
        textTransform: "uppercase",
        borderRadius: "9999px",
        padding: "0.2rem 0.55rem",
        cursor: saving ? "not-allowed" : "pointer",
        opacity: saving ? 0.6 : 1,
        appearance: "none",
        WebkitAppearance: "none",
        minHeight: "26px",
      }}
      className="transition-colors hover:brightness-110"
    >
      {OPTIONS.map((s) => (
        <option
          key={s}
          value={s}
          style={{
            background: "#181818",
            color: "#F5F1E8",
          }}
        >
          {CONFIG[s].label}
        </option>
      ))}
    </select>
  );
}
