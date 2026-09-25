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
import type { DashboardStats } from "@/lib/types";

// ── Types ──────────────────────────────────────────────────────────────────────

interface DashStats {
  hasResume: boolean | null;
  lastSync: string | null;
}

// Background auto-scoring poll: how often to check, and how long to wait
// before giving up and just reporting whatever progress was made.
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

  // Polling refs — survive re-renders without re-triggering effects
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
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

  useEffect(() => stopPolling, [stopPolling]);

  const startScoringPoll = useCallback(
    (runId: string, total: number) => {
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

          setScoring({
            total: s.total,
            scored: s.scored,
            failed: s.failed,
          });

          if (s.status === "completed") {
            const noun = s.scored === 1 ? "job" : "jobs";
            await finish(
              `Scored ${s.scored} of ${s.total} ${noun} against your resume.`,
              "success",
            );
          } else if (s.failed > 0 && s.pending === 0) {
            await finish(
              `Scoring stopped (${s.failed} errors, ${s.scored} scored).`,
              "info",
            );
          }
        } catch {
          // Transient poll read failure — retry next tick
        }
      };

      pollTimerRef.current = setInterval(check, SCORING_POLL_INTERVAL_MS);

      pollTimeoutRef.current = setTimeout(async () => {
        if (pollTokenRef.current !== token) return;
        try {
          const s = await getScoringStatus(runId);
          const scored = s.scored;
          const totalJobs = s.total;
          await finish(
            `Scored ${scored} of ${totalJobs} jobs before poll timeout.`,
            "info",
          );
        } catch {
          await finish("Scoring is taking longer than expected.", "info");
        }
      }, SCORING_POLL_TIMEOUT_MS);

      check();
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
      <PageHeader
        title="Dashboard"
        subtitle="Your internship search & AI matching cockpit"
        action={
          <Button
            onClick={handleSync}
            loading={syncing || !!scoring}
            disabled={syncing || !!scoring}
            size="md"
          >
            {syncing
              ? "Syncing…"
              : scoring
                ? `Scoring ${scoring.scored + scoring.failed}/${scoring.total}…`
                : "🔄 Sync Jobs"}
          </Button>
        }
      />

      {/* ── Stat cards ───────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
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

      {/* ── Recommendation metrics ──────────────────────────────────── */}
      <div className="mb-6 sm:mb-8">
        <p
          className="text-xs uppercase tracking-wider font-semibold mb-3"
          style={{ color: "var(--color-muted)" }}
        >
          Match & Application Metrics
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
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
                label="Scored Jobs"
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
                label="Best Match"
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
                label="Submitted"
                value={dashStats ? String(dashStats.applications_submitted) : "—"}
                icon="📨"
              />
            </>
          )}
        </div>
      </div>

      {/* ── Top Matches + Match Quality ─────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 mb-6 sm:mb-8">
        <div className="lg:col-span-2">
          <TopMatches
            matches={dashStats?.top_matches ?? []}
            loading={loading}
            hasResume={stats.hasResume ?? false}
          />
        </div>
        <div>
          <MatchQualityBreakdown
            breakdown={dashStats?.quality_breakdown ?? null}
            loading={loading}
            hasResume={stats.hasResume ?? false}
          />
        </div>
      </div>

      {/* ── Quick actions ─────────────────────────────────────────── */}
      <div className="mb-8">
        <p
          className="text-xs uppercase tracking-wider font-semibold mb-3"
          style={{ color: "var(--color-muted)" }}
        >
          Quick Actions
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <QuickAction
            href="/jobs"
            icon="🔍"
            label="Browse jobs"
            desc="Explore all aggregated internships"
          />
          <QuickAction
            href="/resume"
            icon="📎"
            label="Manage resume"
            desc="Update profile for AI match scoring"
          />
          <QuickAction
            href="/resume-review"
            icon="📝"
            label="Resume Gap Analyzer"
            desc="Analyze resume against any job description"
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
    <Card padding="md" hoverable={!!href} className="h-full card-elevated">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p
            style={{
              color: "var(--color-muted)",
              fontSize: "0.6875rem",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              fontWeight: 600,
            }}
            className="truncate"
          >
            {label}
          </p>
          <p
            style={{
              fontSize: "1.5rem",
              fontWeight: 800,
              color: valueColor ?? "var(--color-text)",
              lineHeight: 1.2,
              marginTop: "0.25rem",
            }}
            className="truncate"
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
              className="truncate"
            >
              {sub}
            </p>
          )}
        </div>
        <span className="text-xl sm:text-2xl opacity-60 flex-shrink-0">{icon}</span>
      </div>
    </Card>
  );

  if (href)
    return (
      <Link href={href} className="block transition-transform hover:-translate-y-0.5">
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
    <Link href={href} className="block transition-transform hover:-translate-y-0.5">
      <Card
        padding="md"
        hoverable
        className="flex items-center gap-3.5 cursor-pointer card-elevated h-full"
      >
        <span className="text-2xl flex-shrink-0 opacity-80">{icon}</span>
        <div className="min-w-0">
          <p
            style={{
              fontWeight: 600,
              fontSize: "0.875rem",
              color: "var(--color-text)",
            }}
            className="truncate"
          >
            {label}
          </p>
          <p
            style={{
              fontSize: "0.75rem",
              color: "var(--color-subtle)",
              marginTop: "0.15rem",
            }}
            className="truncate"
          >
            {desc}
          </p>
        </div>
      </Card>
    </Link>
  );
}
