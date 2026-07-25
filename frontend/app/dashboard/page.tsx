"use client";

import { useState, useEffect, useCallback } from "react";
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
  runScraper,
  ApiClientError,
} from "@/lib/api";
import type { ScraperRun, DashboardStats } from "@/lib/types";

// ── Types ──────────────────────────────────────────────────────────────────────

interface DashStats {
  hasResume: boolean | null;
  lastSync: string | null;
}

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

  const loadStats = useCallback(async () => {
    setLoading(true);
    try {
      const [s, d] = await Promise.allSettled([
        fetchStats(),
        getDashboardStats(),
      ]);
      if (s.status === "fulfilled") setStats(s.value);
      if (d.status === "fulfilled") setDashStats(d.value);
    } catch {
      // partial — already set nulls
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  async function handleSync() {
    if (syncing) return;
    setSyncing(true);
    try {
      const result = await runScraper();
      const total = result.total_new;
      const scored = result.total_scored;
      const scoredNote = scored > 0 ? ` (${scored} auto-scored)` : "";
      addToast(
        `Sync complete — ${total} new job${total !== 1 ? "s" : ""} added.${scoredNote}`,
        "success",
      );
      await loadStats();
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
          loading={syncing}
          disabled={syncing}
          size="md"
          style={{ marginTop: "0.25rem", flexShrink: 0 }}
        >
          {syncing ? "Syncing…" : "🔄 Sync Jobs"}
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
