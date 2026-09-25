"use client";

import { useState, useEffect, useCallback } from "react";
import { use } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ScoreBadge } from "@/components/jobs/ScoreBadge";
import { StatusBadge } from "@/components/jobs/StatusBadge";
import { NeedsRescoreBadge } from "@/components/jobs/NeedsRescoreBadge";
import { RecommendationBadge } from "@/components/jobs/RecommendationBadge";
import { ResumeRequiredBadge } from "@/components/jobs/ResumeRequiredBadge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorState } from "@/components/ui/ErrorState";
import { ToastContainer, useToast } from "@/components/ui/Toast";
import {
  getJob,
  getResume,
  updateJob,
  scoreJob,
  generateInterviewPrep,
  ApiClientError,
} from "@/lib/api";
import type {
  Job,
  JobStatus,
  ScoreResponse,
  InterviewPrepResponse,
} from "@/lib/types";
import { InterviewPrepPanel } from "@/components/interview-prep/InterviewPrepPanel";

interface Props {
  params: Promise<{ id: string }>;
}

const STATUS_OPTIONS: { value: JobStatus; label: string }[] = [
  { value: "saved", label: "Saved" },
  { value: "applied", label: "Applied" },
  { value: "interview", label: "Interview" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
];

// ── Page ───────────────────────────────────────────────────────────────────────

export default function JobDetailPage({ params }: Props) {
  const { id } = use(params);
  const { toasts, addToast, dismiss } = useToast();

  const [job, setJob] = useState<Job | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Resume presence
  const [hasResume, setHasResume] = useState<boolean | null>(null);

  // Score state
  const [scoreResult, setScoreResult] = useState<ScoreResponse | null>(null);
  const [scoring, setScoring] = useState(false);

  // Interview prep state
  const [interviewPrep, setInterviewPrep] =
    useState<InterviewPrepResponse | null>(null);
  const [generatingPrep, setGeneratingPrep] = useState(false);

  // Status update
  const [status, setStatus] = useState<JobStatus>("saved");
  const [savingStatus, setSavingStatus] = useState(false);

  // Notes
  const [notes, setNotes] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);
  const [notesDirty, setNotesDirty] = useState(false);

  // ── Load ────────────────────────────────────────────────────────────────────

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const j = await getJob(id);
      setJob(j);
      setStatus(j.status);
      setNotes(j.notes ?? "");
      if (j.match_score !== null && j.match_summary !== null) {
        setScoreResult({
          match_score: j.match_score,
          missing_skills: j.missing_skills ?? [],
          match_summary: j.match_summary,
          matched_at: j.matched_at ?? "",
          cached: true,
          needs_rescore: j.needs_rescore,
          recommendation_label: j.recommendation_label,
        });
      }
    } catch (err) {
      setLoadError(
        err instanceof ApiClientError ? err.message : "Failed to load job.",
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    getResume()
      .then((r) => setHasResume(r !== null))
      .catch(() => setHasResume(null));
  }, []);

  // ── Score ────────────────────────────────────────────────────────────────────

  async function handleScore() {
    if (scoring) return;
    setScoring(true);
    try {
      const result = await scoreJob(id);
      setScoreResult(result);
      const updated = await getJob(id);
      setJob(updated);
      addToast(
        `Scored ${result.match_score}% match${result.cached ? " (cached)" : ""}.`,
        "success",
      );
    } catch (err) {
      addToast(
        err instanceof ApiClientError ? err.message : "Scoring failed.",
        "error",
      );
    } finally {
      setScoring(false);
    }
  }

  // ── Interview Prep ───────────────────────────────────────────────────────────

  async function handleGenerateInterviewPrep() {
    if (generatingPrep) return;
    setGeneratingPrep(true);
    try {
      const result = await generateInterviewPrep(id);
      setInterviewPrep(result);
    } catch (err) {
      addToast(
        err instanceof ApiClientError
          ? err.message
          : "Interview prep generation failed.",
        "error",
      );
    } finally {
      setGeneratingPrep(false);
    }
  }

  // ── Status ───────────────────────────────────────────────────────────────────

  async function handleStatusChange(newStatus: JobStatus) {
    if (savingStatus || newStatus === status) return;
    const prev = status;
    setStatus(newStatus);
    setSavingStatus(true);
    try {
      const updated = await updateJob(id, { status: newStatus });
      setJob((prev) => (prev ? { ...prev, status: updated.status } : null));
      addToast(`Status updated to "${newStatus}".`, "success");
    } catch (err) {
      setStatus(prev);
      addToast(
        err instanceof ApiClientError ? err.message : "Failed to update status.",
        "error",
      );
    } finally {
      setSavingStatus(false);
    }
  }

  // ── Notes ────────────────────────────────────────────────────────────────────

  async function handleSaveNotes() {
    if (savingNotes) return;
    setSavingNotes(true);
    try {
      const updated = await updateJob(id, { notes: notes.trim() });
      setJob((prev) => (prev ? { ...prev, notes: updated.notes } : null));
      setNotesDirty(false);
      addToast("Notes saved.", "success");
    } catch (err) {
      addToast(
        err instanceof ApiClientError ? err.message : "Failed to save notes.",
        "error",
      );
    } finally {
      setSavingNotes(false);
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <LoadingSpinner />
        <p className="text-xs uppercase tracking-wider font-semibold" style={{ color: "var(--color-muted)" }}>
          Loading opportunity details…
        </p>
      </div>
    );
  }

  if (loadError)
    return (
      <div>
        <PageHeader title="Job detail" backHref="/jobs" backLabel="Back to Jobs" />
        <ErrorState message={loadError} />
      </div>
    );
  if (!job) return null;

  return (
    <div className="max-w-4xl mx-auto pb-8">
      <PageHeader
        title={job.title}
        subtitle={job.company + (job.location ? ` · ${job.location}` : "")}
        backHref="/jobs"
        backLabel="Back to Jobs"
      />

      {/* ── Badges ───────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2 mb-6">
        <StatusBadge status={status} />
        {hasResume === false ? (
          <ResumeRequiredBadge />
        ) : (
          <>
            <ScoreBadge score={scoreResult?.match_score ?? job.match_score} />
            <RecommendationBadge
              label={
                scoreResult?.recommendation_label ?? job.recommendation_label
              }
            />
            <NeedsRescoreBadge
              needs={scoreResult?.needs_rescore ?? job.needs_rescore}
            />
          </>
        )}
      </div>

      {/* ── Score panel ──────────────────────────────────────────────────── */}
      <Card padding="lg" className="mb-5 card-elevated">
        <p
          className="text-xs uppercase tracking-wider font-semibold mb-3"
          style={{ color: "var(--color-gold)" }}
        >
          AI Compatibility Score
        </p>
        {hasResume === false ? (
          <div>
            <p
              style={{
                color: "var(--color-subtle)",
                fontSize: "0.875rem",
                marginBottom: "0.75rem",
              }}
            >
              Upload a resume to score this job and see how well your skills match.
            </p>
            <Link href="/resume">
              <Button size="sm">Upload Resume</Button>
            </Link>
          </div>
        ) : scoreResult ? (
          <div>
            <div className="flex items-center gap-3 mb-3 flex-wrap">
              <span
                style={{
                  fontSize: "2.25rem",
                  fontWeight: 800,
                  color: "var(--color-text)",
                  lineHeight: 1,
                }}
              >
                {scoreResult.match_score}%
              </span>
              {scoreResult.cached && <Badge color="default">Cached</Badge>}
              {scoreResult.needs_rescore && (
                <Badge color="amber">Needs rescore</Badge>
              )}
            </div>

            <p
              style={{
                fontSize: "0.875rem",
                color: "var(--color-text)",
                lineHeight: 1.65,
                marginBottom: "0.875rem",
              }}
            >
              {scoreResult.match_summary}
            </p>

            {scoreResult.missing_skills.length > 0 && (
              <div className="mt-3">
                <p
                  className="text-xs uppercase tracking-wider font-semibold mb-2"
                  style={{ color: "var(--color-muted)" }}
                >
                  Identified Skill Gaps
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {scoreResult.missing_skills.map((s) => (
                    <Badge key={s} color="red">
                      {s}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-4 pt-3 border-t" style={{ borderColor: "var(--color-border)" }}>
              <Button
                variant="secondary"
                size="sm"
                loading={scoring}
                disabled={scoring}
                onClick={handleScore}
              >
                {scoring ? "Scoring…" : "↻ Re-score with Latest Profile"}
              </Button>
            </div>
          </div>
        ) : (
          <div>
            <p
              style={{
                color: "var(--color-subtle)",
                fontSize: "0.875rem",
                marginBottom: "0.75rem",
              }}
            >
              No score calculated yet. Run AI scoring against your uploaded resume.
            </p>
            <Button
              size="sm"
              loading={scoring}
              disabled={scoring}
              onClick={handleScore}
            >
              {scoring ? "Scoring…" : "⭐ Score Job Now"}
            </Button>
          </div>
        )}
      </Card>

      {/* ── Interview Prep ──────────────────────────────────────────────── */}
      <Card padding="lg" className="mb-5 card-elevated">
        <p
          className="text-xs uppercase tracking-wider font-semibold mb-3"
          style={{ color: "var(--color-gold)" }}
        >
          AI Interview Preparation
        </p>
        {hasResume === false ? (
          <div>
            <p
              style={{
                color: "var(--color-subtle)",
                fontSize: "0.875rem",
                marginBottom: "0.75rem",
              }}
            >
              Upload a resume to generate interview preparation material for this job.
            </p>
            <Link href="/resume">
              <Button size="sm">Upload Resume</Button>
            </Link>
          </div>
        ) : interviewPrep ? (
          <div>
            <InterviewPrepPanel result={interviewPrep} />
            <div className="mt-4 pt-3 border-t" style={{ borderColor: "var(--color-border)" }}>
              <Button
                variant="secondary"
                size="sm"
                loading={generatingPrep}
                disabled={generatingPrep}
                onClick={handleGenerateInterviewPrep}
              >
                {generatingPrep ? "Generating…" : "↻ Regenerate Questions"}
              </Button>
            </div>
          </div>
        ) : (
          <div>
            <p
              style={{
                color: "var(--color-subtle)",
                fontSize: "0.875rem",
                marginBottom: "0.75rem",
              }}
            >
              Generate tailored interview questions, revision topics, and strategy tips based on this job and your resume.
            </p>
            <Button
              size="sm"
              loading={generatingPrep}
              disabled={generatingPrep}
              onClick={handleGenerateInterviewPrep}
            >
              {generatingPrep ? "Generating…" : "🧠 Generate Interview Prep"}
            </Button>
          </div>
        )}
      </Card>

      {/* ── Status dropdown ──────────────────────────────────────────────── */}
      <Card padding="md" className="mb-5 card-elevated">
        <p
          className="text-xs uppercase tracking-wider font-semibold mb-2.5"
          style={{ color: "var(--color-muted)" }}
        >
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
              padding: "0.45rem 0.85rem",
              fontSize: "0.85rem",
              cursor: savingStatus ? "not-allowed" : "pointer",
              opacity: savingStatus ? 0.6 : 1,
            }}
            className="focus:outline-none focus:border-[var(--color-gold)] transition-colors min-h-[38px]"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value} style={{ background: "#161616", color: "#F5F1E8" }}>
                {o.label}
              </option>
            ))}
          </select>
          {savingStatus && (
            <span style={{ fontSize: "0.75rem", color: "var(--color-muted)" }}>
              Updating…
            </span>
          )}
        </div>
      </Card>

      {/* ── Notes ────────────────────────────────────────────────────────── */}
      <Card padding="md" className="mb-5 card-elevated">
        <p
          className="text-xs uppercase tracking-wider font-semibold mb-2.5"
          style={{ color: "var(--color-muted)" }}
        >
          Application Notes
        </p>
        <textarea
          value={notes}
          onChange={(e) => {
            setNotes(e.target.value);
            setNotesDirty(true);
          }}
          placeholder="Add notes about your application, recruiter contacts, or referral details…"
          rows={4}
          style={{
            width: "100%",
            background: "var(--color-bg)",
            border: "1px solid var(--color-border)",
            borderRadius: "0.375rem",
            color: "var(--color-text)",
            padding: "0.6rem 0.85rem",
            fontSize: "0.85rem",
            resize: "vertical",
            fontFamily: "inherit",
            lineHeight: 1.6,
          }}
          className="focus:outline-none focus:border-[var(--color-gold)] transition-colors"
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
            <span style={{ fontSize: "0.75rem", color: "var(--color-green)" }}>
              ✓ Saved
            </span>
          )}
        </div>
      </Card>

      {/* ── Description ──────────────────────────────────────────────────── */}
      <Card padding="lg" className="mb-6 card-elevated">
        <p
          className="text-xs uppercase tracking-wider font-semibold mb-3"
          style={{ color: "var(--color-muted)" }}
        >
          Role Description
        </p>
        <p
          style={{
            color: "var(--color-text)",
            fontSize: "0.875rem",
            lineHeight: 1.75,
            whiteSpace: "pre-wrap",
          }}
        >
          {job.description}
        </p>
      </Card>

      {/* ── Links ────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            background: "var(--color-accent)",
            color: "#F5F1E8",
            border: "1px solid var(--color-accent-border)",
            padding: "0.5rem 1.25rem",
            borderRadius: "0.375rem",
            fontSize: "0.875rem",
            fontWeight: 600,
          }}
          className="btn-fx inline-flex items-center gap-1.5"
        >
          Apply on Site →
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
              padding: "0.5rem 1.25rem",
              borderRadius: "0.375rem",
              fontSize: "0.875rem",
              fontWeight: 500,
            }}
            className="btn-fx inline-flex items-center gap-1.5"
          >
            Company Website
          </a>
        )}
      </div>

      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
