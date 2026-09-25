import { Badge } from "@/components/ui/Badge";
import { BackButton } from "@/components/ui/BackButton";
import type { Resume } from "@/lib/types";

interface ResumePageHeaderProps {
  resume: Resume | null;
  backHref?: string;
  backLabel?: string;
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

export function ResumePageHeader({
  resume,
  backHref,
  backLabel,
}: ResumePageHeaderProps) {
  return (
    <div className="pb-6 mb-6" style={{ borderBottom: "1px solid var(--color-border)" }}>
      {backHref && backLabel && (
        <div className="mb-3">
          <BackButton fallbackHref={backHref} label={backLabel} />
        </div>
      )}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1
              className="text-xl sm:text-2xl font-bold tracking-tight"
              style={{ color: "var(--color-text)" }}
            >
              Resume Profile
            </h1>
            {resume ? (
              <Badge color="green" dot>
                Active
              </Badge>
            ) : (
              <Badge color="default">No Resume Uploaded</Badge>
            )}
          </div>
          <p
            className="text-xs sm:text-sm mt-1.5 max-w-xl leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            Manage your resume profile to drive AI matching, gap analysis, and tailored interview preparation.
          </p>
          {resume && (
            <p className="text-xs mt-2" style={{ color: "var(--color-muted)" }}>
              Last updated {formatRelative(resume.uploaded_at)}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
