"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { ToastContainer, useToast } from "@/components/ui/Toast";
import { TopMatches } from "@/components/dashboard/TopMatches";
import { MatchQualityBreakdown } from "@/components/dashboard/MatchQualityBreakdown";
import { StatCardSkeleton } from "@/components/ui/Skeleton";
import {
  getResume,
  getScraperStatus,
  getDashboardStats,
  getScoringStatus,
  runScraper,
  ApiClientError,
} from "@/lib/api";
import type { ScraperRun, DashboardStats } from "@/lib/types";

// ── Types ──────────────────────────────────────────────────────────────────────

interface DashStats {
  hasResume: boolean | null;
  lastSync: string | null;
}

// Background auto-scoring poll: how often to check, and how long to wait
// before giving up and just reporting whatever progress was made. Chosen
// generously — Gemini calls can take 10-30s each with up to 3 retries
// (see gemini_client._BACKOFF_SECONDS), and new jobs are scored one at a
// time, so a couple of slow/retried jobs can legitimately take a while.
const SCORING_POLL_INTERVAL_MS = 2_000;
const SCORING_POLL_TIMEOUT_MS = 90_000;

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

async function fetchStats(): Promise<DashStats> {
  const [resumeResult, scraperResult] = await Promise.allSettled([
    getResume(),
    getScraperStatus(),
  ]);

  const hasResume =
    resumeResult.status === "fulfilled" ? resumeResult.value !== null : null;
  const lastSync =
    scraperResult.status === "fulfilled"
      ? (scraperResult.value[0]?.completed_at ?? null)
      : null;

  return { hasResume, lastSync };
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { toasts, addToast, dismiss } = useToast();
  const [stats, setStats] = useState<DashStats>({
    hasResume: null,
    lastSync: null,
  });
  const [dashStats, setDashStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [scoring, setScoring] = useState<{
    total: number;
    scored: number;
    failed: number;
  } | null>(null);

  // Polling refs — a ref (not state) so timer ids survive re-renders without
  // re-triggering effects, and so cleanup always sees the latest ids.
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Bumped every time a new poll session starts; stale async callbacks from
  // a previous session compare against this and bail out instead of acting.
  const pollTokenRef = useRef(0);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  }, []);

  const loadStats = useCallback(async (): Promise<{
    hasResume: boolean | null;
  }> => {
    setLoading(true);
    let hasResume: boolean | null = null;
    try {
      const [s, d] = await Promise.allSettled([
        fetchStats(),
        getDashboardStats(),
      ]);
      if (s.status === "fulfilled") {
        setStats(s.value);
        hasResume = s.value.hasResume;
      }
      if (d.status === "fulfilled") setDashStats(d.value);
    } catch {
      // partial — already set nulls
    } finally {
      setLoading(false);
    }
    return { hasResume };
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // Stop any in-flight poll on unmount — no orphan timers.
  useEffect(() => stopPolling, [stopPolling]);

  const startScoringPoll = useCallback(
    (runId: string, total: number) => {
      // A repeated sync click could in principle race a previous poll —
      // cancel it first so there's never more than one interval running.
      stopPolling();
      const token = ++pollTokenRef.current;
      setScoring({ total, scored: 0, failed: 0 });

      const finish = async (message: string, kind: "success" | "info") => {
        if (pollTokenRef.current !== token) return;
        stopPolling();
        setScoring(null);
        addToast(message, kind);
        await loadStats();
      };

      const check = async () => {
        if (pollTokenRef.current !== token) return;
        try {
          const s = await getScoringStatus(runId);
          if (pollTokenRef.current !== token) return;
          setScoring({ total: s.total, scored: s.scored, failed: s.failed });

          if (s.status === "completed") {
            const message =
              s.failed > 0
                ? `Scoring complete — ${s.scored} scored, ${s.failed} failed.`
                : `Scoring complete — ${s.scored} job${s.scored !== 1 ? "s" : ""} scored.`;
            await finish(message, "success");
          }
        } catch {
          // Transient failure reaching the status endpoint — keep polling
          // on the next tick rather than tearing down already-loaded
          // dashboard state (edge case: scoring-status request fails).
        }
      };

      pollTimerRef.current = setInterval(check, SCORING_POLL_INTERVAL_MS);
      pollTimeoutRef.current = setTimeout(async () => {
        if (pollTokenRef.current !== token) return;
        // Safety fallback only — normal completion comes from the backend
        // reporting status "completed", never from this timing out.
        try {
          const s = await getScoringStatus(runId);
          if (pollTokenRef.current !== token) return;
          await finish(
            `Still scoring — ${s.scored + s.failed} of ${s.total} done so far.`,
            "info",
          );
        } catch {
          await finish("Scoring is taking longer than expected.", "info");
        }
      }, SCORING_POLL_TIMEOUT_MS);

      check(); // don't wait a full interval for the first read
    },
    [stopPolling, addToast, loadStats],
  );

  async function handleSync() {
    if (syncing || scoring) return;
    setSyncing(true);
    try {
      const result = await runScraper();
      const total = result.total_new;
      addToast(
        `Sync complete — ${total} new job${total !== 1 ? "s" : ""} found.`,
        "success",
      );
      const { hasResume } = await loadStats();

      if (total > 0 && hasResume && result.scoring_run_id) {
        startScoringPoll(result.scoring_run_id, result.new_job_ids.length);
      }
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Sync failed.";
      addToast(msg, "error");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-6 flex-wrap">
        <PageHeader
          title="Dashboard"
          subtitle="Your internship search at a glance"
        />
        <Button
          onClick={handleSync}
          loading={syncing || !!scoring}
          disabled={syncing || !!scoring}
          size="md"
          style={{ marginTop: "0.25rem", flexShrink: 0 }}
        >
          {syncing
            ? "Syncing…"
            : scoring
              ? `Scoring ${scoring.scored + scoring.failed}/${scoring.total}…`
              : "🔄 Sync Jobs"}
        </Button>
      </div>

      {/* ── Stat cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {loading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : (
          <>
            <StatCard
              label="Total Jobs"
              value={dashStats ? String(dashStats.total_jobs) : "—"}
              icon="💼"
              href="/jobs"
            />
            <StatCard
              label="Resume"
              value={
                stats.hasResume === null
                  ? "—"
                  : stats.hasResume
                    ? "Uploaded"
                    : "None"
              }
              icon="📄"
              href="/resume"
              valueColor={
                stats.hasResume ? "var(--color-green)" : "var(--color-amber)"
              }
            />
            <StatCard
              label="Last Sync"
              value={stats.lastSync ? formatRelative(stats.lastSync) : "Never"}
              icon="🔄"
            />
            <StatCard
              label="Top Match"
              value={
                !stats.hasResume
                  ? "—"
                  : dashStats?.best_match_score != null
                    ? `${dashStats.best_match_score}%`
                    : "—"
              }
              icon="⭐"
              href={
                !stats.hasResume
                  ? "/resume"
                  : dashStats?.top_matches[0]?.id
                    ? `/jobs/${dashStats.top_matches[0].id}`
                    : undefined
              }
              valueColor="var(--color-green)"
              sub={
                !stats.hasResume
                  ? "Upload Resume"
                  : (dashStats?.top_matches[0]?.company ?? undefined)
              }
            />
          </>
        )}
      </div>

      {/* ── Recommendation metrics (Phase 5) ────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {loading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : (
          <>
            <StatCard
              label="Previously Scored Jobs"
              value={dashStats ? String(dashStats.scored_jobs) : "—"}
              icon="🧮"
            />
            <StatCard
              label="Average Match"
              value={
                !stats.hasResume
                  ? "—"
                  : dashStats?.average_match_score != null
                    ? `${dashStats.average_match_score}%`
                    : "—"
              }
              icon="📊"
              href={!stats.hasResume ? "/resume" : undefined}
              sub={!stats.hasResume ? "Upload Resume" : undefined}
            />
            <StatCard
              label="Best Match Score"
              value={
                !stats.hasResume
                  ? "—"
                  : dashStats?.best_match_score != null
                    ? `${dashStats.best_match_score}%`
                    : "—"
              }
              icon="🏆"
              valueColor="var(--color-green)"
              href={!stats.hasResume ? "/resume" : undefined}
              sub={!stats.hasResume ? "Upload Resume" : undefined}
            />
            <StatCard
              label="Applications Submitted"
              value={dashStats ? String(dashStats.applications_submitted) : "—"}
              icon="📨"
            />
          </>
        )}
      </div>

      {/* ── Top Matches + Match Quality (Phase 5) ───────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
        <div className="lg:col-span-2">
          <TopMatches
            matches={dashStats?.top_matches ?? []}
            loading={loading}
            hasResume={stats.hasResume ?? false}
          />
        </div>
        <MatchQualityBreakdown
          breakdown={dashStats?.quality_breakdown ?? null}
          loading={loading}
          hasResume={stats.hasResume ?? false}
        />
      </div>

      {/* ── Quick actions ─────────────────────────────────────────── */}
      <div className="mb-8">
        <h2
          className="text-sm font-semibold uppercase tracking-wide mb-3"
          style={{ color: "var(--color-muted)" }}
        >
          Quick actions
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <QuickAction
            href="/jobs"
            icon="🔍"
            label="Browse jobs"
            desc="View all fetched internships"
          />
          <QuickAction
            href="/resume"
            icon="📎"
            label="Upload resume"
            desc="Enable AI match scoring"
          />
        </div>
      </div>

      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  icon,
  href,
  valueColor,
  sub,
}: {
  label: string;
  value: string;
  icon: string;
  href?: string;
  valueColor?: string;
  sub?: string;
}) {
  const inner = (
    <Card padding="md" hoverable={!!href} className="h-full">
      <div className="flex items-start justify-between">
        <div>
          <p
            style={{
              color: "var(--color-muted)",
              fontSize: "0.72rem",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              fontWeight: 600,
            }}
          >
            {label}
          </p>
          <p
            style={{
              fontSize: "1.6rem",
              fontWeight: 700,
              color: valueColor ?? "var(--color-text)",
              lineHeight: 1.2,
              marginTop: "0.3rem",
            }}
          >
            {value}
          </p>
          {sub && (
            <p
              style={{
                color: "var(--color-subtle)",
                fontSize: "0.75rem",
                marginTop: "0.2rem",
              }}
            >
              {sub}
            </p>
          )}
        </div>
        <span style={{ fontSize: "1.4rem", opacity: 0.7 }}>{icon}</span>
      </div>
    </Card>
  );

  if (href)
    return (
      <Link href={href} className="block hover:opacity-90 transition-opacity">
        {inner}
      </Link>
    );
  return inner;
}

function QuickAction({
  href,
  icon,
  label,
  desc,
}: {
  href: string;
  icon: string;
  label: string;
  desc: string;
}) {
  return (
    <Link href={href}>
      <Card
        padding="md"
        hoverable
        className="flex items-center gap-3 cursor-pointer"
      >
        <span style={{ fontSize: "1.5rem" }}>{icon}</span>
        <div>
          <p
            style={{
              fontWeight: 600,
              fontSize: "0.875rem",
              color: "var(--color-text)",
            }}
          >
            {label}
          </p>
          <p
            style={{
              fontSize: "0.775rem",
              color: "var(--color-subtle)",
              marginTop: "0.1rem",
            }}
          >
            {desc}
          </p>
        </div>
      </Card>
    </Link>
  );
}
