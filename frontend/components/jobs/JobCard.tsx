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
        style={{
          borderColor: "var(--color-border)",
        }}
      >
        <div className="flex items-start justify-between gap-4">
          {/* Left: title + meta */}
          <div className="min-w-0 flex-1">
            <p
              className="font-semibold truncate group-hover:underline"
              style={{ color: "var(--color-text)", fontSize: "0.95rem" }}
            >
              {job.title}
            </p>
            <p
              className="text-sm mt-0.5 truncate"
              style={{ color: "var(--color-subtle)" }}
            >
              {job.company}
              {job.location && (
                <span style={{ color: "var(--color-muted)" }}>
                  {" "}
                  · {job.location}
                </span>
              )}
            </p>

            {/* Badges row */}
            <div className="flex flex-wrap gap-1.5 mt-2">
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

          {/* Right: source + date */}
          <div className="text-right flex-shrink-0">
            <p style={{ color: "var(--color-muted)", fontSize: "0.75rem" }}>
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
