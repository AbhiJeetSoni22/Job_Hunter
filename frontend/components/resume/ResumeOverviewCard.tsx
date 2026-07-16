"use client";

import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { getResumeQuality } from "@/lib/categorizeSkills";
import type { Resume } from "@/lib/types";

interface ResumeOverviewCardProps {
  resume: Resume;
  onDelete: () => void;
  deleting?: boolean;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function MetricTile({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div
      className="p-4 rounded-lg"
      style={{
        background: "var(--color-bg)",
        border: "1px solid var(--color-border)",
      }}
    >
      <p
        className="text-[0.65rem] uppercase tracking-wider font-semibold"
        style={{ color: "var(--color-muted)" }}
      >
        {label}
      </p>
      <p
        className="text-lg font-semibold mt-1 truncate"
        style={{ color: "var(--color-text)" }}
        title={String(value)}
      >
        {value}
      </p>
      {sub && (
        <p className="text-xs mt-0.5 truncate" style={{ color: "var(--color-subtle)" }}>
          {sub}
        </p>
      )}
    </div>
  );
}

function FileIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

export function ResumeOverviewCard({
  resume,
  onDelete,
  deleting = false,
}: ResumeOverviewCardProps) {
  const quality = getResumeQuality(resume.skills.length);

  return (
    <Card padding="none" className="card-elevated overflow-hidden fade-up-1">
      <div
        className="px-5 py-4 flex items-start justify-between gap-3"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{
              background: "rgba(99,102,241,0.12)",
              color: "var(--color-accent-h)",
              border: "1px solid rgba(99,102,241,0.2)",
            }}
          >
            <FileIcon />
          </div>
          <div className="min-w-0">
            <h2
              className="text-sm font-semibold"
              style={{ color: "var(--color-text)" }}
            >
              Resume Overview
            </h2>
            <p
              className="text-xs mt-0.5 truncate"
              style={{ color: "var(--color-subtle)" }}
              title={resume.filename}
            >
              {resume.filename}
            </p>
          </div>
        </div>
        <Badge color={quality.color}>{quality.label}</Badge>
      </div>

      <div className="p-5">
        <div className="grid grid-cols-2 gap-3">
          <MetricTile
            label="Skills Detected"
            value={resume.skills.length}
            sub="From AI extraction"
          />
          <MetricTile
            label="Uploaded"
            value={formatDate(resume.uploaded_at).split(",")[0]}
            sub={formatDate(resume.uploaded_at).split(", ").slice(1).join(", ")}
          />
        </div>

        <p
          className="text-xs mt-4 px-3 py-2.5 rounded-lg"
          style={{
            color: "var(--color-subtle)",
            background: "var(--color-bg)",
            border: "1px solid var(--color-border)",
          }}
        >
          {quality.description}
        </p>

        <div className="mt-4 pt-4 flex items-center justify-between gap-3 flex-wrap">
          <p className="text-xs" style={{ color: "var(--color-muted)" }}>
            Uploading a new PDF replaces this profile.
          </p>
          <Button
            variant="danger"
            size="sm"
            loading={deleting}
            disabled={deleting}
            onClick={onDelete}
          >
            {deleting ? "Deleting…" : "Delete Resume"}
          </Button>
        </div>
      </div>
    </Card>
  );
}
