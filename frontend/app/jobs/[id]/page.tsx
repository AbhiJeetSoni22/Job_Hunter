import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { ScoreBadge } from "@/components/jobs/ScoreBadge";
import { StatusBadge } from "@/components/jobs/StatusBadge";
import { NeedsRescoreBadge } from "@/components/jobs/NeedsRescoreBadge";
import { ErrorState } from "@/components/ui/ErrorState";
import { getJob } from "@/lib/api";
import { ApiClientError } from "@/lib/api";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function JobDetailPage({ params }: Props) {
  const { id } = await params;

  try {
    const job = await getJob(id);

    return (
      <div className="max-w-3xl">
        <PageHeader
          title={job.title}
          subtitle={job.company + (job.location ? ` · ${job.location}` : "")}
        />

        {/* Badges */}
        <div className="flex flex-wrap gap-2 mb-6">
          <StatusBadge status={job.status} />
          <ScoreBadge score={job.match_score} />
          <NeedsRescoreBadge needs={job.needs_rescore} />
        </div>

        {/* Description */}
        <Card padding="md" className="mb-4">
          <p className="text-xs uppercase tracking-wide mb-2" style={{ color: "var(--color-muted)" }}>
            Description
          </p>
          <p style={{ color: "var(--color-text)", fontSize: "0.875rem", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
            {job.description}
          </p>
        </Card>

        {/* Links */}
        <div className="flex gap-3">
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              background: "var(--color-accent)",
              color: "white",
              padding: "0.4rem 1rem",
              borderRadius: "0.375rem",
              fontSize: "0.875rem",
              fontWeight: 500,
            }}
          >
            Apply →
          </a>
          {job.company_url && (
            <a
              href={job.company_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                background: "var(--color-surface)",
                color: "var(--color-text)",
                border: "1px solid var(--color-border)",
                padding: "0.4rem 1rem",
                borderRadius: "0.375rem",
                fontSize: "0.875rem",
                fontWeight: 500,
              }}
            >
              Company site
            </a>
          )}
        </div>

        <p className="mt-6 text-xs" style={{ color: "var(--color-muted)" }}>
          Full scoring and status controls coming in Phase 3C.
        </p>
      </div>
    );
  } catch (err) {
    const message = err instanceof ApiClientError ? err.message : "Failed to load job.";
    return (
      <div>
        <PageHeader title="Job detail" />
        <ErrorState message={message} />
      </div>
    );
  }
}
