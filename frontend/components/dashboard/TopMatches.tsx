"use client";

import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { StatusSelect } from "@/components/jobs/StatusSelect";
import { RecommendationBadge } from "@/components/jobs/RecommendationBadge";
import { ScoreRing } from "@/components/ui/Motion";
import { TopMatchRowSkeleton } from "@/components/ui/Skeleton";
import type { TopMatchItem, JobStatus } from "@/lib/types";

interface TopMatchesProps {
  matches: TopMatchItem[];
  loading: boolean;
  /** When false, no active resume exists — match data has no basis. */
  hasResume: boolean;
  onStatusChanged?: (jobId: string, newStatus: JobStatus) => void;
  onStatusError?: (message: string) => void;
}

const SOURCE_LABEL: Record<string, string> = {
  remoteok: "RemoteOK",
  yc_jobs: "YC Jobs",
};

export function TopMatches({
  matches,
  loading,
  hasResume,
  onStatusChanged,
  onStatusError,
}: TopMatchesProps) {
  return (
    <Card
      padding="none"
      className="card-elevated overflow-hidden border h-full flex flex-col justify-between"
      style={{ borderColor: "var(--color-accent-border)" }}
    >
      {/* Card Header Bar */}
      <div
        className="flex items-center justify-between px-4 sm:px-6 py-4 border-b"
        style={{
          borderColor: "var(--color-border)",
          background: "linear-gradient(180deg, rgba(143, 23, 51, 0.09) 0%, transparent 100%)",
        }}
      >
        <div className="flex items-center gap-2.5">
          <span className="text-lg" style={{ color: "var(--color-gold)" }}>⭐</span>
          <div>
            <h2
              className="text-base sm:text-lg font-extrabold tracking-tight"
              style={{ color: "var(--color-text)" }}
            >
              Recommended For You
            </h2>
            <p className="text-xs mt-0.5" style={{ color: "var(--color-subtle)" }}>
              High-relevance opportunities scored by Gemini AI
            </p>
          </div>
        </div>

        <Link href="/jobs?scored=true" className="text-xs font-semibold hover:underline hidden sm:inline-block" style={{ color: "var(--color-gold)" }}>
          View all scored →
        </Link>
      </div>

      {/* Content Area */}
      <div className="flex-1">
        {loading ? (
          <ul className="divide-y" style={{ borderColor: "var(--color-border)" }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <li key={i}>
                <TopMatchRowSkeleton />
              </li>
            ))}
          </ul>
        ) : !hasResume ? (
          <div className="p-6">
            <EmptyState
              icon="📄"
              title="Upload your resume to unlock AI-powered job matching"
              description="Personalized recommendations, match scores (0–100%), and missing skill analysis appear here once you upload your resume."
              action={
                <Link href="/resume">
                  <Button size="md">Upload Resume Now</Button>
                </Link>
              }
            />
          </div>
        ) : matches.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon="🎯"
              title="No scored opportunities yet"
              description="Click 'Sync Jobs' above to pull fresh openings and score them against your technical profile."
              action={
                <Link href="/jobs">
                  <Button size="sm" variant="secondary">Browse All Jobs</Button>
                </Link>
              }
            />
          </div>
        ) : (
          <ul className="divide-y" style={{ borderColor: "var(--color-border)" }}>
            {matches.map((job, idx) => (
              <li key={job.id}>
                <Link
                  href={`/jobs/${job.id}`}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 px-4 sm:px-6 py-4 hover:bg-[var(--color-surface-hover)] transition-all group card-interactive"
                >
                  {/* Left: Rank & Title & Company */}
                  <div className="flex items-start gap-3.5 min-w-0 flex-1">
                    <span
                      className="font-mono text-xs font-bold pt-1.5 flex-shrink-0 w-6 text-center"
                      style={{ color: idx === 0 ? "var(--color-gold)" : "var(--color-muted)" }}
                    >
                      #{idx + 1}
                    </span>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span
                          className="text-[0.6875rem] font-bold uppercase tracking-wider px-2 py-0.5 rounded"
                          style={{
                            background: "var(--color-bg)",
                            color: "var(--color-subtle)",
                            border: "1px solid var(--color-border)",
                          }}
                        >
                          {SOURCE_LABEL[job.source] ?? job.source}
                        </span>
                        <RecommendationBadge label={job.recommendation_label} />
                      </div>

                      <h3
                        className="font-bold text-sm sm:text-base mt-1.5 truncate group-hover:text-[var(--color-gold)] transition-colors"
                        style={{ color: "var(--color-text)" }}
                      >
                        {job.title}
                      </h3>

                      <p
                        className="text-xs truncate mt-0.5"
                        style={{ color: "var(--color-subtle)" }}
                      >
                        <span className="font-semibold text-[var(--color-text)]">{job.company}</span>
                      </p>
                    </div>
                  </div>

                  {/* Right: Circular ScoreRing + StatusSelect + Inspect Action */}
                  <div className="flex items-center gap-3 sm:gap-4 flex-shrink-0 self-start sm:self-auto pl-9 sm:pl-0 w-full sm:w-auto justify-between sm:justify-end border-t sm:border-t-0 pt-2.5 sm:pt-0">
                    {/* Status Select dropdown */}
                    <div onClick={(e) => e.stopPropagation()}>
                      <StatusSelect
                        jobId={job.id}
                        status={job.status}
                        onChanged={onStatusChanged}
                        onError={onStatusError}
                      />
                    </div>

                    {/* Animated ScoreRing */}
                    <div className="flex items-center gap-2">
                      <ScoreRing score={job.match_score} size="sm" showLabel />
                    </div>

                    {/* Arrow CTA */}
                    <span
                      className="hidden sm:inline-flex items-center text-xs font-semibold group-hover:translate-x-0.5 transition-transform"
                      style={{ color: "var(--color-muted)" }}
                    >
                      →
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Card Footer Bar */}
      {matches.length > 0 && (
        <div
          className="px-4 sm:px-6 py-3 border-t flex items-center justify-between text-xs"
          style={{
            borderColor: "var(--color-border)",
            background: "var(--color-bg)",
          }}
        >
          <span style={{ color: "var(--color-muted)" }}>
            Showing top {matches.length} matches
          </span>
          <Link href="/jobs" className="font-medium hover:underline" style={{ color: "var(--color-gold)" }}>
            Explore full database →
          </Link>
        </div>
      )}
    </Card>
  );
}
