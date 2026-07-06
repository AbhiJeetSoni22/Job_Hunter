import { JobCard } from "./JobCard";
import { EmptyState } from "@/components/ui/EmptyState";
import type { JobListItem, JobStatus } from "@/lib/types";

interface JobListProps {
  jobs: JobListItem[];
  onStatusChanged?: (jobId: string, newStatus: JobStatus) => void;
  onStatusError?: (message: string) => void;
  /** When false, no active resume exists — match badges have no basis. */
  hasResume?: boolean;
}

export function JobList({
  jobs,
  onStatusChanged,
  onStatusError,
  hasResume = true,
}: JobListProps) {
  if (jobs.length === 0) {
    return (
      <EmptyState
        icon="📭"
        title="No jobs found"
        description="Run the scraper to fetch new internship listings."
      />
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {jobs.map((job) => (
        <JobCard
          key={job.id}
          job={job}
          onStatusChanged={onStatusChanged}
          onStatusError={onStatusError}
          hasResume={hasResume}
        />
      ))}
    </div>
  );
}
