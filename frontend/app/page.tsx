import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { getJobs, getResume, getScraperStatus } from "@/lib/api";
import Link from "next/link";

// Server Component — data fetched at request time
export default async function DashboardPage() {
  // Parallel fetches; individual failures show placeholder rather than crash
  const [jobsResult, resume, scraperStatus] = await Promise.allSettled([
    getJobs({ page: 1, page_size: 1 }),
    getResume(),
    getScraperStatus(),
  ]);

  const totalJobs    = jobsResult.status    === "fulfilled" ? jobsResult.value.total       : null;
  const hasResume    = resume.status        === "fulfilled" ? resume.value !== null         : null;
  const lastSync     = scraperStatus.status === "fulfilled" ? scraperStatus.value[0]?.completed_at : null;

  const topMatchResult = await (async () => {
    if (jobsResult.status !== "fulfilled" || jobsResult.value.total === 0) return null;
    try {
      const scored = await getJobs({ sort_by: "match_score", order: "desc", page_size: 1, scored: true });
      return scored.jobs[0] ?? null;
    } catch { return null; }
  })();

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Your internship search at a glance"
      />

      {/* ── Stat cards ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Jobs"
          value={totalJobs !== null ? String(totalJobs) : "—"}
          icon="💼"
          href="/jobs"
        />
        <StatCard
          label="Resume"
          value={hasResume === null ? "—" : hasResume ? "Uploaded" : "None"}
          icon="📄"
          href="/resume"
          valueColor={hasResume ? "var(--color-green)" : "var(--color-amber)"}
        />
        <StatCard
          label="Last Sync"
          value={lastSync ? formatRelative(lastSync) : "Never"}
          icon="🔄"
        />
        <StatCard
          label="Top Match"
          value={topMatchResult ? `${topMatchResult.match_score}%` : "—"}
          icon="⭐"
          href={topMatchResult ? `/jobs/${topMatchResult.id}` : undefined}
          valueColor="var(--color-green)"
          sub={topMatchResult?.company}
        />
      </div>

      {/* ── Quick actions ───────────────────────────────────────── */}
      <div className="mb-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide mb-3" style={{ color: "var(--color-muted)" }}>
          Quick actions
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <QuickAction href="/jobs"   icon="🔍" label="Browse jobs" desc="View all fetched internships" />
          <QuickAction href="/resume" icon="📎" label="Upload resume" desc="Enable AI match scoring" />
        </div>
      </div>
    </div>
  );
}

// ── Sub-components (server-safe, no state) ────────────────────────────────────

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
      <Card
        padding="md"
        className="flex items-center gap-3 hover:opacity-90 transition-opacity cursor-pointer"
      >
        <span style={{ fontSize: "1.5rem" }}>{icon}</span>
        <div>
          <p style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--color-text)" }}>{label}</p>
          <p style={{ fontSize: "0.775rem", color: "var(--color-subtle)", marginTop: "0.1rem" }}>{desc}</p>
        </div>
      </Card>
    </Link>
  );
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1)   return "Just now";
  if (mins < 60)  return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)   return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
