import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { ScoreBadge } from "./ScoreBadge";
import { StatusSelect } from "./StatusSelect";
import { NeedsRescoreBadge } from "./NeedsRescoreBadge";
import { RecommendationBadge } from "./RecommendationBadge";
import { ResumeRequiredBadge } from "./ResumeRequiredBadge";
import type { JobListItem, JobStatus } from "@/lib/types";

interface JobCardProps {
  job: JobListItem;
  onStatusChanged?: (jobId: string, newStatus: JobStatus) => void;
  onStatusError?: (message: string) => void;
  /** When false, no active resume exists — match badges have no basis. */
  hasResume?: boolean;
}

const SOURCE_LABEL: Record<string, string> = {
  remoteok: "RemoteOK",
  yc_jobs: "YC Jobs",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function JobCard({
  job,
  onStatusChanged,
  onStatusError,
  hasResume = true,
}: JobCardProps) {
  return (
    <Link href={`/jobs/${job.id}`} className="block group">
      <Card
        padding="md"
        hoverable
        className="card-elevated"
        style={{
          borderColor: "var(--color-border)",
        }}
      >
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 sm:gap-4">
          {/* Main content: title + meta */}
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2 sm:block">
              <h3
                className="font-semibold text-sm sm:text-base leading-snug group-hover:text-[var(--color-text)] transition-colors break-words"
                style={{ color: "var(--color-text)" }}
              >
                {job.title}
              </h3>

              {/* Source/date on extra small mobile screens when stacked */}
              <div className="text-right flex-shrink-0 sm:hidden">
                <span className="text-[0.7rem] uppercase tracking-wider block" style={{ color: "var(--color-muted)" }}>
                  {SOURCE_LABEL[job.source] ?? job.source}
                </span>
                <span className="text-[0.6875rem] block mt-0.5" style={{ color: "var(--color-muted)" }}>
                  {formatDate(job.posted_at ?? job.created_at)}
                </span>
              </div>
            </div>

            <p
              className="text-xs sm:text-sm mt-1 truncate"
              style={{ color: "var(--color-subtle)" }}
            >
              <span className="font-medium text-[var(--color-text)] opacity-90">{job.company}</span>
              {job.location && (
                <span style={{ color: "var(--color-muted)" }}>
                  {" "}· {job.location}
                </span>
              )}
            </p>

            {/* Badges row */}
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mt-3">
              <StatusSelect
                jobId={job.id}
                status={job.status}
                onChanged={onStatusChanged}
                onError={onStatusError}
              />
              {hasResume ? (
                <>
                  <ScoreBadge score={job.match_score} />
                  <RecommendationBadge label={job.recommendation_label} />
                  <NeedsRescoreBadge needs={job.needs_rescore} />
                </>
              ) : (
                <ResumeRequiredBadge />
              )}
            </div>
          </div>

          {/* Desktop Right: source + date */}
          <div className="hidden sm:block text-right flex-shrink-0 pl-2">
            <p className="text-[0.75rem] uppercase tracking-wider font-medium" style={{ color: "var(--color-muted)" }}>
              {SOURCE_LABEL[job.source] ?? job.source}
            </p>
            <p
              style={{
                color: "var(--color-muted)",
                fontSize: "0.75rem",
                marginTop: "0.25rem",
              }}
            >
              {formatDate(job.posted_at ?? job.created_at)}
            </p>
          </div>
        </div>
      </Card>
    </Link>
  );
}
