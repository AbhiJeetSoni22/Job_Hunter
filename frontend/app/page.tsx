"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { ToastContainer, useToast } from "@/components/ui/Toast";
import {
  getJobs,
  getResume,
  getScraperStatus,
  runScraper,
  ApiClientError,
} from "@/lib/api";
import type { ScraperRun } from "@/lib/types";

// ── Types ──────────────────────────────────────────────────────────────────────

interface DashStats {
  totalJobs:    number | null;
  hasResume:    boolean | null;
  lastSync:     string | null;
  topScore:     number | null;
  topCompany:   string | null;
  topJobId:     string | null;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1)  return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

async function fetchStats(): Promise<DashStats> {
  const [jobsResult, resumeResult, scraperResult] = await Promise.allSettled([
    getJobs({ page: 1, page_size: 1 }),
    getResume(),
    getScraperStatus(),
  ]);

  const totalJobs  = jobsResult.status    === "fulfilled" ? jobsResult.value.total           : null;
  const hasResume  = resumeResult.status  === "fulfilled" ? resumeResult.value !== null       : null;
  const lastSync   = scraperResult.status === "fulfilled" ? (scraperResult.value[0]?.completed_at ?? null) : null;

  // Top-scored job
  let topScore:   number | null = null;
  let topCompany: string | null = null;
  let topJobId:   string | null = null;

  if (jobsResult.status === "fulfilled" && jobsResult.value.total > 0) {
    try {
      const scored = await getJobs({ sort_by: "match_score", order: "desc", page_size: 1, scored: true });
      const top = scored.jobs[0] ?? null;
      if (top) {
        topScore   = top.match_score;
        topCompany = top.company;
        topJobId   = top.id;
      }
    } catch { /* no scored jobs — leave null */ }
  }

  return { totalJobs, hasResume, lastSync, topScore, topCompany, topJobId };
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { toasts, addToast, dismiss } = useToast();
  const [stats, setStats]     = useState<DashStats>({ totalJobs: null, hasResume: null, lastSync: null, topScore: null, topCompany: null, topJobId: null });
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const loadStats = useCallback(async () => {
    setLoading(true);
    try {
      const s = await fetchStats();
      setStats(s);
    } catch {
      // partial — already set nulls
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  async function handleSync() {
    if (syncing) return;
    setSyncing(true);
    try {
      const result = await runScraper();
      const total = result.total_new;
      addToast(`Sync complete — ${total} new job${total !== 1 ? "s" : ""} added.`, "success");
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
        <StatCard
          label="Total Jobs"
          value={loading ? "…" : (stats.totalJobs !== null ? String(stats.totalJobs) : "—")}
          icon="💼"
          href="/jobs"
        />
        <StatCard
          label="Resume"
          value={loading ? "…" : (stats.hasResume === null ? "—" : stats.hasResume ? "Uploaded" : "None")}
          icon="📄"
          href="/resume"
          valueColor={stats.hasResume ? "var(--color-green)" : "var(--color-amber)"}
        />
        <StatCard
          label="Last Sync"
          value={loading ? "…" : (stats.lastSync ? formatRelative(stats.lastSync) : "Never")}
          icon="🔄"
        />
        <StatCard
          label="Top Match"
          value={loading ? "…" : (stats.topScore !== null ? `${stats.topScore}%` : "—")}
          icon="⭐"
          href={stats.topJobId ? `/jobs/${stats.topJobId}` : undefined}
          valueColor="var(--color-green)"
          sub={stats.topCompany ?? undefined}
        />
      </div>

      {/* ── Quick actions ─────────────────────────────────────────── */}
      <div className="mb-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide mb-3" style={{ color: "var(--color-muted)" }}>
          Quick actions
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <QuickAction href="/jobs"   icon="🔍" label="Browse jobs"   desc="View all fetched internships" />
          <QuickAction href="/resume" icon="📎" label="Upload resume" desc="Enable AI match scoring"     />
        </div>
      </div>

      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatCard({
  label, value, icon, href, valueColor, sub,
}: {
  label: string; value: string; icon: string;
  href?: string; valueColor?: string; sub?: string;
}) {
  const inner = (
    <Card padding="md" className="h-full">
      <div className="flex items-start justify-between">
        <div>
          <p style={{ color: "var(--color-muted)", fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>
            {label}
          </p>
          <p style={{ fontSize: "1.6rem", fontWeight: 700, color: valueColor ?? "var(--color-text)", lineHeight: 1.2, marginTop: "0.3rem" }}>
            {value}
          </p>
          {sub && <p style={{ color: "var(--color-subtle)", fontSize: "0.75rem", marginTop: "0.2rem" }}>{sub}</p>}
        </div>
        <span style={{ fontSize: "1.4rem", opacity: 0.7 }}>{icon}</span>
      </div>
    </Card>
  );

  if (href) return <Link href={href} className="block hover:opacity-90 transition-opacity">{inner}</Link>;
  return inner;
}

function QuickAction({ href, icon, label, desc }: { href: string; icon: string; label: string; desc: string }) {
  return (
    <Link href={href}>
      <Card padding="md" className="flex items-center gap-3 hover:opacity-90 transition-opacity cursor-pointer">
        <span style={{ fontSize: "1.5rem" }}>{icon}</span>
        <div>
          <p style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--color-text)" }}>{label}</p>
          <p style={{ fontSize: "0.775rem", color: "var(--color-subtle)", marginTop: "0.1rem" }}>{desc}</p>
        </div>
      </Card>
    </Link>
  );
}