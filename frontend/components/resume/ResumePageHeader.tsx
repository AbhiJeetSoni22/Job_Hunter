import { Badge } from "@/components/ui/Badge";
import type { Resume } from "@/lib/types";

interface ResumePageHeaderProps {
  resume: Resume | null;
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function ResumePageHeader({ resume }: ResumePageHeaderProps) {
  return (
    <div
      className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 pb-6 mb-6"
      style={{ borderBottom: "1px solid var(--color-border)" }}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-3 flex-wrap">
          <h1
            className="text-2xl font-bold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            Resume Profile
          </h1>
          {resume ? (
            <Badge color="green" dot>
              Active
            </Badge>
          ) : (
            <Badge color="default">Not Uploaded</Badge>
          )}
        </div>
        <p
          className="text-sm mt-1.5 max-w-xl"
          style={{ color: "var(--color-subtle)" }}
        >
          Upload and manage your resume to unlock AI-powered job matching,
          gap analysis, and personalized recommendations.
        </p>
        {resume && (
          <p className="text-xs mt-2" style={{ color: "var(--color-muted)" }}>
            Last updated {formatRelative(resume.uploaded_at)}
          </p>
        )}
      </div>
    </div>
  );
}
