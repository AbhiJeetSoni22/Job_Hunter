"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { ToastContainer, useToast } from "@/components/ui/Toast";
import { TopMatches } from "@/components/dashboard/TopMatches";
import { MatchQualityBreakdown } from "@/components/dashboard/MatchQualityBreakdown";
import { StatCardSkeleton } from "@/components/ui/Skeleton";
import { useAuth } from "@/components/auth/AuthContext";
import {
  getResume,
  getScraperStatus,
  getDashboardStats,
  getScoringStatus,
  runScraper,
  ApiClientError,
} from "@/lib/api";
import type { DashboardStats, JobStatus, TopMatchItem } from "@/lib/types";

// ── Types ──────────────────────────────────────────────────────────────────────

interface DashStats {
  hasResume: boolean | null;
  lastSync: string | null;
}

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

function getTimeOfDayGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
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

// ── Page Component ─────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { user } = useAuth();
  const { toasts, addToast, dismiss } = useToast();

  const [stats, setStats] = useState<DashStats>({
    hasResume: null,
    lastSync: null,
  });
  const [dashStats, setDashStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter state for dashboard recommendations
  const [searchQuery, setSearchQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState<"all" | "remoteok" | "yc_jobs">("all");
  const [minScoreFilter, setMinScoreFilter] = useState<number | null>(null);

  const [scoring, setScoring] = useState<{
    total: number;
    scored: number;
    failed: number;
  } | null>(null);

  // Polling refs
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
    setError(null);
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
      if (d.status === "fulfilled") {
        setDashStats(d.value);
      } else if (d.reason) {
        setError(d.reason instanceof ApiClientError ? d.reason.message : "Failed to load dashboard statistics.");
      }
    } catch {
      setError("An unexpected error occurred while loading dashboard data.");
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

  // Optimistic status update handler
  const handleStatusChanged = useCallback((jobId: string, newStatus: JobStatus) => {
    setDashStats((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        top_matches: prev.top_matches.map((item) =>
          item.id === jobId ? { ...item, status: newStatus } : item,
        ),
      };
    });
    addToast(`Job status updated to ${newStatus}.`, "success");
  }, [addToast]);

  // Filtered top matches for quick exploration
  const filteredMatches: TopMatchItem[] = useMemo(() => {
    if (!dashStats?.top_matches) return [];
    return dashStats.top_matches.filter((job) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesQuery =
          job.title.toLowerCase().includes(q) ||
          job.company.toLowerCase().includes(q);
        if (!matchesQuery) return false;
      }
      if (sourceFilter !== "all" && job.source !== sourceFilter) {
        return false;
      }
      if (minScoreFilter !== null && job.match_score < minScoreFilter) {
        return false;
      }
      return true;
    });
  }, [dashStats?.top_matches, searchQuery, sourceFilter, minScoreFilter]);

  // Contextual personalized greeting
  const greetingName = user?.name ? user.name.split(" ")[0] : user?.email ? user.email.split("@")[0] : "there";
  const greeting = `${getTimeOfDayGreeting()}, ${greetingName}`;

  return (
    <div className="flex flex-col gap-6 sm:gap-8 pb-12">
      {/* ── 1. Contextual Header ───────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-1 sm:pt-2">
        <div>
          <h1
            className="text-2xl sm:text-3xl font-extrabold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            {greeting}
          </h1>
          <p
            className="text-xs sm:text-sm mt-1"
            style={{ color: "var(--color-subtle)" }}
          >
            Here are the technical opportunities worth looking at today.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap sm:flex-nowrap">
          <Button
            onClick={handleSync}
            loading={syncing || !!scoring}
            disabled={syncing || !!scoring}
            size="md"
            className="font-semibold gap-2"
          >
            {syncing
              ? "Syncing Boards…"
              : scoring
                ? `Scoring ${scoring.scored + scoring.failed}/${scoring.total}…`
                : "🔄 Sync Jobs"}
          </Button>

          <Link href="/jobs">
            <Button size="md" variant="secondary">
              Browse All Jobs →
            </Button>
          </Link>
        </div>
      </div>

      {/* ── Error Banner if API fails ──────────────────────────────── */}
      {error && (
        <div
          className="p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
          style={{ background: "rgba(239, 68, 68, 0.08)", borderColor: "rgba(239, 68, 68, 0.3)" }}
        >
          <div className="flex items-center gap-2">
            <span style={{ color: "var(--color-red)" }}>⚠️</span>
            <span style={{ color: "var(--color-red)", fontWeight: 600 }}>{error}</span>
          </div>
          <Button size="sm" variant="secondary" onClick={loadStats}>
            Try Again
          </Button>
        </div>
      )}

      {/* ── 2. Resume / AI Readiness Status Banner ──────────────────── */}
      {!loading && stats.hasResume === false && (
        <div
          className="p-4 sm:p-5 rounded-xl border card-elevated flex flex-col sm:flex-row sm:items-center justify-between gap-4"
          style={{
            background: "linear-gradient(90deg, var(--color-surface) 0%, rgba(143, 23, 51, 0.15) 100%)",
            borderColor: "var(--color-accent-border)",
          }}
        >
          <div className="flex items-start gap-3.5">
            <span className="p-2.5 rounded-lg text-xl flex-shrink-0" style={{ background: "rgba(143, 23, 51, 0.2)" }}>
              📄
            </span>
            <div>
              <p className="font-bold text-sm sm:text-base" style={{ color: "var(--color-text)" }}>
                AI Match Scoring Is Inactive
              </p>
              <p className="text-xs sm:text-sm mt-0.5 leading-relaxed" style={{ color: "var(--color-subtle)" }}>
                Upload your resume once to unlock 0–100% fit scores, skill gap alerts, and personalized recommendations.
              </p>
            </div>
          </div>
          <Link href="/resume" className="flex-shrink-0">
            <Button size="md" className="w-full sm:w-auto font-semibold">
              Upload Resume →
            </Button>
          </Link>
        </div>
      )}

      {!loading && stats.hasResume === true && (
        <div
          className="px-4 py-2.5 rounded-lg border flex items-center justify-between text-xs"
          style={{
            background: "var(--color-surface)",
            borderColor: "var(--color-border)",
          }}
        >
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ background: "var(--color-green)" }} />
            <span className="font-medium" style={{ color: "var(--color-text)" }}>
              Resume Active · AI Matching Enabled
            </span>
            {stats.lastSync && (
              <span className="hidden md:inline text-[0.7rem]" style={{ color: "var(--color-muted)" }}>
                · Last Synced {formatRelative(stats.lastSync)}
              </span>
            )}
          </div>
          <Link href="/resume" className="font-semibold hover:underline" style={{ color: "var(--color-gold)" }}>
            Manage Profile →
          </Link>
        </div>
      )}

      {/* ── 3. Discovery & Scoring Key Metrics ──────────────────────── */}
      <div>
        <p
          className="text-xs uppercase tracking-wider font-semibold mb-3"
          style={{ color: "var(--color-muted)" }}
        >
          Overview & Metrics
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
                label="Total Jobs"
                value={dashStats ? String(dashStats.total_jobs) : "—"}
                icon="💼"
                href="/jobs"
                sub="RemoteOK + YC"
              />
              <StatCard
                label="Scored Jobs"
                value={dashStats ? String(dashStats.scored_jobs) : "—"}
                icon="🧮"
                href="/jobs?scored=true"
                sub="Evaluated by Gemini"
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
                valueColor={dashStats?.average_match_score && dashStats.average_match_score >= 70 ? "var(--color-green)" : undefined}
                sub={!stats.hasResume ? "Upload Resume" : "Overall candidate fit"}
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
                icon="🏆"
                valueColor="var(--color-green)"
                href={
                  !stats.hasResume
                    ? "/resume"
                    : dashStats?.top_matches[0]?.id
                      ? `/jobs/${dashStats.top_matches[0].id}`
                      : undefined
                }
                sub={
                  !stats.hasResume
                    ? "Upload Resume"
                    : (dashStats?.top_matches[0]?.company ?? "Highest relevance")
                }
              />
            </>
          )}
        </div>
      </div>

      {/* ── 4. Search & Quick Filters for Dashboard ─────────────────── */}
      {dashStats && dashStats.top_matches.length > 0 && (
        <div
          className="p-3 sm:p-4 rounded-xl border flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3"
          style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
        >
          {/* Search Input */}
          <div className="relative flex-1">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs" style={{ color: "var(--color-muted)" }}>
              🔍
            </span>
            <input
              type="text"
              placeholder="Search recommendations by title or company…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-lg text-xs"
              style={{
                background: "var(--color-bg)",
                border: "1px solid var(--color-border)",
                color: "var(--color-text)",
              }}
            />
          </div>

          {/* Quick Filter Chips */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              onClick={() => {
                setSourceFilter("all");
                setMinScoreFilter(null);
                setSearchQuery("");
              }}
              className="px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-colors"
              style={{
                background: sourceFilter === "all" && minScoreFilter === null ? "var(--color-surface-hover)" : "transparent",
                color: sourceFilter === "all" && minScoreFilter === null ? "var(--color-text)" : "var(--color-subtle)",
                border: "1px solid var(--color-border)",
              }}
            >
              All
            </button>
            <button
              onClick={() => setMinScoreFilter(minScoreFilter === 80 ? null : 80)}
              className="px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-colors"
              style={{
                background: minScoreFilter === 80 ? "rgba(34, 197, 94, 0.15)" : "transparent",
                color: minScoreFilter === 80 ? "var(--color-green)" : "var(--color-subtle)",
                border: "1px solid var(--color-border)",
              }}
            >
              ≥ 80% Match
            </button>
            <button
              onClick={() => setSourceFilter(sourceFilter === "remoteok" ? "all" : "remoteok")}
              className="px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-colors"
              style={{
                background: sourceFilter === "remoteok" ? "var(--color-surface-hover)" : "transparent",
                color: sourceFilter === "remoteok" ? "var(--color-text)" : "var(--color-subtle)",
                border: "1px solid var(--color-border)",
              }}
            >
              RemoteOK
            </button>
            <button
              onClick={() => setSourceFilter(sourceFilter === "yc_jobs" ? "all" : "yc_jobs")}
              className="px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-colors"
              style={{
                background: sourceFilter === "yc_jobs" ? "var(--color-surface-hover)" : "transparent",
                color: sourceFilter === "yc_jobs" ? "var(--color-text)" : "var(--color-subtle)",
                border: "1px solid var(--color-border)",
              }}
            >
              YC Jobs
            </button>
          </div>
        </div>
      )}

      {/* ── 5. Recommended Jobs (Centerpiece) + Match Quality ───────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 sm:gap-6 items-stretch">
        <div className="lg:col-span-8">
          <TopMatches
            matches={filteredMatches}
            loading={loading}
            hasResume={stats.hasResume ?? false}
            onStatusChanged={handleStatusChanged}
            onStatusError={(msg) => addToast(msg, "error")}
          />
        </div>

        <div className="lg:col-span-4">
          <MatchQualityBreakdown
            breakdown={dashStats?.quality_breakdown ?? null}
            loading={loading}
            hasResume={stats.hasResume ?? false}
          />
        </div>
      </div>

      {/* ── 6. Application Pipeline Summary ────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p
            className="text-xs uppercase tracking-wider font-semibold"
            style={{ color: "var(--color-muted)" }}
          >
            Application Pipeline
          </p>
          <Link href="/jobs" className="text-xs font-medium hover:underline" style={{ color: "var(--color-gold)" }}>
            View in Catalog →
          </Link>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Saved", count: "—", status: "saved", desc: "Bookmarked to review", href: "/jobs?status=saved" },
            { label: "Applied", count: dashStats ? String(dashStats.applications_submitted) : "—", status: "applied", desc: "Submitted to employer", href: "/jobs?status=applied" },
            { label: "Interview", count: "—", status: "interview", desc: "Active conversations", href: "/jobs?status=interview" },
            { label: "Offer", count: "—", status: "offer", desc: "Offers received", href: "/jobs?status=offer" },
          ].map((col) => (
            <Link key={col.label} href={col.href} className="block transition-transform hover:-translate-y-0.5">
              <div
                className="p-3.5 sm:p-4 rounded-xl border card-interactive"
                style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold" style={{ color: "var(--color-text)" }}>
                    {col.label}
                  </span>
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{
                      background:
                        col.status === "offer"
                          ? "var(--color-green)"
                          : col.status === "interview"
                            ? "var(--color-gold)"
                            : col.status === "applied"
                              ? "var(--color-sky)"
                              : "var(--color-muted)",
                    }}
                  />
                </div>
                <p className="text-lg sm:text-xl font-extrabold mt-1" style={{ color: "var(--color-text)" }}>
                  {col.count}
                </p>
                <p className="text-[0.6875rem] mt-0.5 truncate" style={{ color: "var(--color-subtle)" }}>
                  {col.desc}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* ── 7. Quick Actions ────────────────────────────────────────── */}
      <div>
        <p
          className="text-xs uppercase tracking-wider font-semibold mb-3"
          style={{ color: "var(--color-muted)" }}
        >
          Tools & Workflows
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <QuickAction
            href="/jobs"
            icon="🔍"
            label="Browse All Jobs"
            desc="Filter by source, scored status, and keyword"
          />
          <QuickAction
            href="/resume"
            icon="📎"
            label="Manage Resume & Skills"
            desc="Update profile for fresh AI match scores"
          />
          <QuickAction
            href="/resume-review"
            icon="📝"
            label="Resume Gap Analyzer"
            desc="Deep-dive analysis against any job description"
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
    <Card padding="md" hoverable={!!href} className="h-full card-interactive border" style={{ borderColor: "var(--color-border)" }}>
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
              fontSize: "1.6rem",
              fontWeight: 800,
              color: valueColor ?? "var(--color-text)",
              lineHeight: 1.15,
              marginTop: "0.3rem",
            }}
            className="truncate"
          >
            {value}
          </p>
          {sub && (
            <p
              style={{
                color: "var(--color-subtle)",
                fontSize: "0.72rem",
                marginTop: "0.25rem",
              }}
              className="truncate"
            >
              {sub}
            </p>
          )}
        </div>
        <span className="text-xl sm:text-2xl opacity-70 flex-shrink-0">{icon}</span>
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
        className="flex items-center gap-3.5 cursor-pointer card-interactive h-full border"
        style={{ borderColor: "var(--color-border)" }}
      >
        <span className="text-2xl flex-shrink-0 opacity-80">{icon}</span>
        <div className="min-w-0">
          <p
            style={{
              fontWeight: 700,
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
