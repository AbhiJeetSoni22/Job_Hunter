import { PageHeader } from "@/components/ui/PageHeader";
import { JobList } from "@/components/jobs/JobList";
import { ErrorState } from "@/components/ui/ErrorState";
import { getJobs } from "@/lib/api";
import { ApiClientError } from "@/lib/api";

export const metadata = { title: "Jobs — AI Internship Hunter" };

export default async function JobsPage() {
  try {
    const result = await getJobs({ page: 1, page_size: 20, sort_by: "created_at", order: "desc" });

    return (
      <div>
        <PageHeader
          title="Jobs"
          subtitle={`${result.total} internship${result.total !== 1 ? "s" : ""} in database`}
        />
        <JobList jobs={result.jobs} />
      </div>
    );
  } catch (err) {
    const message = err instanceof ApiClientError ? err.message : "Failed to load jobs.";
    return (
      <div>
        <PageHeader title="Jobs" />
        <ErrorState message={message} />
      </div>
    );
  }
}
