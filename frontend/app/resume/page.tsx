import { PageHeader } from "@/components/ui/PageHeader";
import { ResumeInfoCard } from "@/components/resume/ResumeInfoCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { getResume } from "@/lib/api";

export const metadata = { title: "Resume — AI Internship Hunter" };

export default async function ResumePage() {
  const resume = await getResume();

  return (
    <div className="max-w-xl">
      <PageHeader
        title="Resume"
        subtitle="Upload a PDF to enable AI match scoring"
      />

      {resume ? (
        <ResumeInfoCard resume={resume} />
      ) : (
        <EmptyState
          icon="📎"
          title="No resume uploaded"
          description="Upload a PDF resume to start scoring jobs against your skills."
        />
      )}

      <p className="mt-6 text-xs" style={{ color: "var(--color-muted)" }}>
        Upload and delete controls coming in Phase 3C.
      </p>
    </div>
  );
}
