import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScoreBadge } from "@/components/jobs/ScoreBadge";
import { StatusBadge } from "@/components/jobs/StatusBadge";
import { RecommendationBadge } from "@/components/jobs/RecommendationBadge";
import type { TopMatchItem } from "@/lib/types";

interface TopMatchesProps {
  matches: TopMatchItem[];
  loading: boolean;
}

const SOURCE_LABEL: Record<string, string> = {
  remoteok: "RemoteOK",
  yc_jobs: "YC Jobs",
};

export function TopMatches({ matches, loading }: TopMatchesProps) {
  return (
    <Card padding="none" style={{ borderColor: "var(--color-accent)", borderWidth: "1.5px" }}>
      <div
        className="flex items-center justify-between px-5 py-4"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        <div className="flex items-center gap-2">
          <span style={{ fontSize: "1.1rem" }}>⭐</span>
          <h2 style={{ fontWeight: 700, fontSize: "1rem", color: "var(--color-text)" }}>
            Top Matches
          </h2>
        </div>
        <span style={{ fontSize: "0.7rem", color: "var(--color-subtle)" }}>
          Best 5 by AI match score
        </span>
      </div>

      {loading ? (
        <div className="px-5 py-8 text-center" style={{ color: "var(--color-subtle)" }}>
          Loading…
        </div>
      ) : matches.length === 0 ? (
        <EmptyState
          icon="🎯"
          title="No scored jobs yet"
          description="Sync jobs and score them against your resume to see your best matches here."
        />
      ) : (
        <ul>
          {matches.map((job, idx) => (
            <li key={job.id} style={{ borderBottom: idx < matches.length - 1 ? "1px solid var(--color-border)" : "none" }}>
              <Link
                href={`/jobs/${job.id}`}
                className="flex items-center gap-4 px-5 py-3 hover:opacity-90 transition-opacity"
              >
                <span
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    color: "var(--color-muted)",
                    width: "1.25rem",
                    flexShrink: 0,
                  }}
                >
                  #{idx + 1}
                </span>

                <div className="flex-1 min-w-0">
                  <p
                    style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--color-text)" }}
                    className="truncate"
                  >
                    {job.title}
                  </p>
                  <p style={{ fontSize: "0.775rem", color: "var(--color-subtle)" }} className="truncate">
                    {job.company} · {SOURCE_LABEL[job.source] ?? job.source}
                  </p>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
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
