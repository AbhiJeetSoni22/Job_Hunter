import { Card } from "@/components/ui/Card";
import { SkillChip } from "./SkillChip";
import type { Resume } from "@/lib/types";

interface ResumeInfoCardProps {
  resume: Resume;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "long", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export function ResumeInfoCard({ resume }: ResumeInfoCardProps) {
  return (
    <Card padding="md">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-semibold" style={{ color: "var(--color-text)" }}>
            {resume.filename}
          </p>
          <p className="text-xs mt-0.5" style={{ color: "var(--color-muted)" }}>
            Uploaded {formatDate(resume.uploaded_at)}
          </p>
        </div>
        <span
          className="text-2xl select-none"
          title="PDF resume"
          aria-hidden
        >
          📄
        </span>
      </div>

      {resume.skills.length > 0 && (
        <div className="mt-4">
          <p className="text-xs mb-2 uppercase tracking-wide" style={{ color: "var(--color-muted)" }}>
            Detected skills ({resume.skills.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {resume.skills.map((skill) => (
              <SkillChip key={skill} skill={skill} />
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
