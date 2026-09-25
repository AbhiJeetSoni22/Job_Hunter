import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { ScoreBadge } from "@/components/jobs/ScoreBadge";
import { StatusBadge } from "@/components/jobs/StatusBadge";
import { RecommendationBadge } from "@/components/jobs/RecommendationBadge";
import { TopMatchRowSkeleton } from "@/components/ui/Skeleton";
import type { TopMatchItem } from "@/lib/types";

interface TopMatchesProps {
  matches: TopMatchItem[];
  loading: boolean;
  /** When false, no active resume exists — match data has no basis. */
  hasResume: boolean;
}

const SOURCE_LABEL: Record<string, string> = {
  remoteok: "RemoteOK",
  yc_jobs: "YC Jobs",
};

export function TopMatches({ matches, loading, hasResume }: TopMatchesProps) {
  return (
    <Card
      padding="none"
      className="card-elevated overflow-hidden"
      style={{ borderColor: "var(--color-accent-border)" }}
    >
      <div
        className="flex items-center justify-between px-4 sm:px-5 py-3.5 sm:py-4"
        style={{
          borderBottom: "1px solid var(--color-border)",
          background: "linear-gradient(180deg, rgba(143, 23, 51, 0.08) 0%, transparent 100%)",
        }}
      >
        <div className="flex items-center gap-2">
          <span className="text-base sm:text-lg" style={{ color: "var(--color-gold)" }}>⭐</span>
          <h2
            style={{
              fontWeight: 700,
              fontSize: "0.95rem",
              color: "var(--color-text)",
            }}
          >
            Top Matches
          </h2>
        </div>
        <span className="text-[0.7rem] uppercase tracking-wider font-medium" style={{ color: "var(--color-muted)" }}>
          Best 5 by AI match
        </span>
      </div>

      {loading ? (
        <ul>
          {Array.from({ length: 5 }).map((_, i) => (
            <li key={i}>
              <TopMatchRowSkeleton />
            </li>
          ))}
        </ul>
      ) : !hasResume ? (
        <EmptyState
          icon="📄"
          title="Upload your resume to unlock AI-powered job matching"
          description="Personalized recommendations and match scores appear here once you upload a resume."
          action={
            <Link href="/resume">
              <Button size="sm">Upload Resume</Button>
            </Link>
          }
        />
      ) : matches.length === 0 ? (
        <EmptyState
          icon="🎯"
          title="No scored jobs yet"
          description="Sync jobs and score them against your resume to see your best matches here."
        />
      ) : (
        <ul className="divide-y" style={{ borderColor: "var(--color-border)" }}>
          {matches.map((job, idx) => (
            <li key={job.id}>
              <Link
                href={`/jobs/${job.id}`}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-4 px-4 sm:px-5 py-3.5 hover:bg-[var(--color-surface-hover)] transition-colors group"
              >
                <div className="flex items-start gap-3 min-w-0 flex-1">
                  <span
                    className="font-mono text-xs font-bold pt-0.5 flex-shrink-0"
                    style={{ color: idx === 0 ? "var(--color-gold)" : "var(--color-muted)" }}
                  >
                    #{idx + 1}
                  </span>

                  <div className="min-w-0 flex-1">
                    <p
                      className="font-semibold text-xs sm:text-sm truncate group-hover:text-[var(--color-text)]"
                      style={{ color: "var(--color-text)" }}
                    >
                      {job.title}
                    </p>
                    <p
                      className="text-xs truncate mt-0.5"
                      style={{ color: "var(--color-subtle)" }}
                    >
                      {job.company} <span style={{ color: "var(--color-muted)" }}>· {SOURCE_LABEL[job.source] ?? job.source}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap sm:flex-nowrap flex-shrink-0 pl-6 sm:pl-0">
                  <RecommendationBadge label={job.recommendation_label} />
                  <StatusBadge status={job.status} />
                  <ScoreBadge score={job.match_score} />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
