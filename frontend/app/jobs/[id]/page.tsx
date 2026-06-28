"use client";

import { useState, useEffect, useCallback } from "react";
import { use } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ScoreBadge } from "@/components/jobs/ScoreBadge";
import { StatusBadge } from "@/components/jobs/StatusBadge";
import { NeedsRescoreBadge } from "@/components/jobs/NeedsRescoreBadge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { ToastContainer, useToast } from "@/components/ui/Toast";
import { getJob, updateJob, scoreJob, ApiClientError } from "@/lib/api";
import type { Job, JobStatus, ScoreResponse } from "@/lib/types";

interface Props {
  params: Promise<{ id: string }>;
}

const STATUS_OPTIONS: { value: JobStatus; label: string }[] = [
  { value: "saved",     label: "Saved"     },
  { value: "applied",   label: "Applied"   },
  { value: "interview", label: "Interview" },
  { value: "offer",     label: "Offer"     },
  { value: "rejected",  label: "Rejected"  },
];

// ── Page ───────────────────────────────────────────────────────────────────────

export default function JobDetailPage({ params }: Props) {
  const { id } = use(params);
  const { toasts, addToast, dismiss } = useToast();

  const [job,         setJob]         = useState<Job | null>(null);
  const [loadError,   setLoadError]   = useState<string | null>(null);
  const [loading,     setLoading]     = useState(true);

  // Score state
  const [scoreResult, setScoreResult]   = useState<ScoreResponse | null>(null);
  const [scoring,     setScoring]       = useState(false);

  // Status update
  const [status,         setStatus]         = useState<JobStatus>("saved");
  const [savingStatus,   setSavingStatus]   = useState(false);

  // Notes
  const [notes,        setNotes]        = useState("");
  const [savingNotes,  setSavingNotes]  = useState(false);
  const [notesDirty,   setNotesDirty]   = useState(false);

  // ── Load ────────────────────────────────────────────────────────────────────

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const j = await getJob(id);
      setJob(j);
      setStatus(j.status);
      setNotes(j.notes ?? "");
      // Populate score panel from stored data if present
      if (j.match_score !== null && j.match_summary !== null) {
        setScoreResult({
          match_score:    j.match_score,
          missing_skills: j.missing_skills ?? [],
          match_summary:  j.match_summary,
          matched_at:     j.matched_at ?? "",
          cached:         true,
          needs_rescore:  j.needs_rescore,
        });
      }
    } catch (err) {
      setLoadError(err instanceof ApiClientError ? err.message : "Failed to load job.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  // ── Score ────────────────────────────────────────────────────────────────────

  async function handleScore() {
    if (scoring) return;
    setScoring(true);
    try {
      const result = await scoreJob(id);
      setScoreResult(result);
      // Refresh job to get updated needs_rescore / match_score badge
      const updated = await getJob(id);
      setJob(updated);
      addToast(`Scored ${result.match_score}% match${result.cached ? " (cached)" : ""}.`, "success");
    } catch (err) {
      addToast(err instanceof ApiClientError ? err.message : "Scoring failed.", "error");
    } finally {
      setScoring(false);
    }
  }

  // ── Status ───────────────────────────────────────────────────────────────────

  async function handleStatusChange(newStatus: JobStatus) {
    if (savingStatus || newStatus === status) return;
    const prev = status;
    setStatus(newStatus); // optimistic
    setSavingStatus(true);
    try {
      await updateJob(id, { status: newStatus });
      setJob((j) => j ? { ...j, status: newStatus } : j);
      addToast(`Status updated to "${newStatus}".`, "success");
    } catch (err) {
      setStatus(prev); // rollback
      addToast(err instanceof ApiClientError ? err.message : "Status update failed.", "error");
    } finally {
      setSavingStatus(false);
    }
  }

  // ── Notes ────────────────────────────────────────────────────────────────────

  async function handleSaveNotes() {
    if (savingNotes) return;
    setSavingNotes(true);
    try {
      await updateJob(id, { notes });
      setJob((j) => j ? { ...j, notes } : j);
      setNotesDirty(false);
      addToast("Notes saved.", "success");
    } catch (err) {
      addToast(err instanceof ApiClientError ? err.message : "Failed to save notes.", "error");
    } finally {
      setSavingNotes(false);
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) return <LoadingSpinner label="Loading job…" />;
  if (loadError) return (
    <div>
      <PageHeader title="Job detail" />
      <ErrorState message={loadError} />
    </div>
  );
  if (!job) return null;

  return (
    <div className="max-w-3xl">
      <PageHeader
        title={job.title}
        subtitle={job.company + (job.location ? ` · ${job.location}` : "")}
      />

      {/* ── Badges ───────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2 mb-6">
        <StatusBadge status={status} />
        <ScoreBadge score={scoreResult?.match_score ?? job.match_score} />
        <NeedsRescoreBadge needs={scoreResult?.needs_rescore ?? job.needs_rescore} />
      </div>

      {/* ── Score panel ──────────────────────────────────────────────────── */}
      <Card padding="md" className="mb-4">
        <p className="text-xs uppercase tracking-wide mb-3" style={{ color: "var(--color-muted)" }}>
          AI Match Score
        </p>
        {scoreResult ? (
          <div>
            <div className="flex items-center gap-3 mb-3 flex-wrap">
              <span style={{ fontSize: "2rem", fontWeight: 700, color: "var(--color-text)" }}>
                {scoreResult.match_score}%
              </span>
              {scoreResult.cached && (
                <Badge color="default">Cached</Badge>
              )}
              {scoreResult.needs_rescore && (
                <Badge color="amber">Needs rescore</Badge>
              )}
            </div>

            <p style={{ fontSize: "0.875rem", color: "var(--color-text)", lineHeight: 1.6, marginBottom: "0.75rem" }}>
              {scoreResult.match_summary}
            </p>

            {scoreResult.missing_skills.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wide mb-1.5" style={{ color: "var(--color-muted)" }}>
                  Missing skills
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {scoreResult.missing_skills.map((s) => (
                    <Badge key={s} color="red">{s}</Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-3">
              <Button
                variant="secondary"
                size="sm"
                loading={scoring}
                disabled={scoring}
                onClick={handleScore}
              >
                {scoring ? "Scoring…" : "↻ Re-score"}
              </Button>
            </div>
          </div>
        ) : (
          <div>
            <p style={{ color: "var(--color-subtle)", fontSize: "0.875rem", marginBottom: "0.75rem" }}>
              No score yet. Click below to run AI match scoring.
            </p>
            <Button
              size="sm"
              loading={scoring}
              disabled={scoring}
              onClick={handleScore}
            >
              {scoring ? "Scoring…" : "⭐ Score Job"}
            </Button>
          </div>
        )}
      </Card>

      {/* ── Status dropdown ──────────────────────────────────────────────── */}
      <Card padding="md" className="mb-4">
        <p className="text-xs uppercase tracking-wide mb-3" style={{ color: "var(--color-muted)" }}>
          Application Status
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          <select
            value={status}
            onChange={(e) => handleStatusChange(e.target.value as JobStatus)}
            disabled={savingStatus}
            style={{
              background: "var(--color-bg)",
              border: "1px solid var(--color-border)",
              borderRadius: "0.375rem",
              color: "var(--color-text)",
              padding: "0.4rem 0.75rem",
              fontSize: "0.875rem",
              cursor: savingStatus ? "not-allowed" : "pointer",
              opacity: savingStatus ? 0.6 : 1,
            }}
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          {savingStatus && (
            <span style={{ fontSize: "0.78rem", color: "var(--color-muted)" }}>Saving…</span>
          )}
        </div>
      </Card>

      {/* ── Notes ────────────────────────────────────────────────────────── */}
      <Card padding="md" className="mb-4">
        <p className="text-xs uppercase tracking-wide mb-3" style={{ color: "var(--color-muted)" }}>
          Notes
        </p>
        <textarea
          value={notes}
          onChange={(e) => { setNotes(e.target.value); setNotesDirty(true); }}
          placeholder="Add notes about this application…"
          rows={4}
          style={{
            width: "100%",
            background: "var(--color-bg)",
            border: "1px solid var(--color-border)",
            borderRadius: "0.375rem",
            color: "var(--color-text)",
            padding: "0.5rem 0.75rem",
            fontSize: "0.875rem",
            resize: "vertical",
            fontFamily: "inherit",
            lineHeight: 1.6,
          }}
        />
        <div className="flex items-center gap-3 mt-3">
          <Button
            size="sm"
            loading={savingNotes}
            disabled={savingNotes || !notesDirty}
            onClick={handleSaveNotes}
          >
            {savingNotes ? "Saving…" : "Save Notes"}
          </Button>
          {!notesDirty && notes && (
            <span style={{ fontSize: "0.78rem", color: "var(--color-muted)" }}>Saved</span>
          )}
        </div>
      </Card>

      {/* ── Description ──────────────────────────────────────────────────── */}
      <Card padding="md" className="mb-4">
        <p className="text-xs uppercase tracking-wide mb-2" style={{ color: "var(--color-muted)" }}>
          Description
        </p>
        <p style={{ color: "var(--color-text)", fontSize: "0.875rem", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
          {job.description}
        </p>
      </Card>

      {/* ── Links ────────────────────────────────────────────────────────── */}
      <div className="flex gap-3">
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            background: "var(--color-accent)",
            color: "white",
            padding: "0.4rem 1rem",
            borderRadius: "0.375rem",
            fontSize: "0.875rem",
            fontWeight: 500,
          }}
        >
          Apply →
        </a>
        {job.company_url && (
          <a
            href={job.company_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              background: "var(--color-surface)",
              color: "var(--color-text)",
              border: "1px solid var(--color-border)",
              padding: "0.4rem 1rem",
              borderRadius: "0.375rem",
              fontSize: "0.875rem",
              fontWeight: 500,
            }}
          >
            Company site
          </a>
        )}
      </div>

      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}