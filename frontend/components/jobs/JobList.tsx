import { JobCard } from "./JobCard";
import { EmptyState } from "@/components/ui/EmptyState";
import type { JobListItem } from "@/lib/types";

interface JobListProps {
  jobs: JobListItem[];
}

export function JobList({ jobs }: JobListProps) {
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
        <JobCard key={job.id} job={job} />
      ))}
    </div>
  );
}
