"use client";

import { useState } from "react";
import Link from "next/link";
import { ScrollReveal } from "@/components/ui/Motion";
import { ScoreBadge } from "@/components/jobs/ScoreBadge";
import { StatusBadge } from "@/components/jobs/StatusBadge";
import { Button } from "@/components/ui/Button";

const SAMPLE_ROLES = [
  {
    id: "1",
    title: "Software Engineer Intern (Frontend)",
    company: "Vectra AI",
    location: "Remote / New York",
    source: "remoteok",
    sourceLabel: "RemoteOK",
    score: 95,
    status: "applied" as const,
    skills: ["React", "TypeScript", "TailwindCSS", "Next.js"],
    posted: "1d ago",
  },
  {
    id: "2",
    title: "Full-Stack Development Intern",
    company: "Helios Dynamics",
    location: "San Francisco, CA",
    source: "yc_jobs",
    sourceLabel: "YC Jobs",
    score: 87,
    status: "saved" as const,
    skills: ["TypeScript", "Node.js", "PostgreSQL", "FastAPI"],
    posted: "2d ago",
  },
  {
    id: "3",
    title: "AI Platform & Engineering Intern",
    company: "Synthesis Cloud",
    location: "Remote / London",
    source: "remoteok",
    sourceLabel: "RemoteOK",
    score: 82,
    status: "interview" as const,
    skills: ["Python", "PyTorch", "Docker", "REST APIs"],
    posted: "3d ago",
  },
];

export function JobDiscoveryPreview() {
  const [activeTab, setActiveTab] = useState<"all" | "remoteok" | "yc_jobs">("all");

  const filteredRoles =
    activeTab === "all"
      ? SAMPLE_ROLES
      : SAMPLE_ROLES.filter((r) => r.source === activeTab);

  return (
    <section className="py-12 sm:py-20 border-t" style={{ borderColor: "var(--color-border)" }}>
      <ScrollReveal animation="fade-up">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
          <div>
            <p
              className="text-xs uppercase tracking-wider font-semibold mb-2"
              style={{ color: "var(--color-gold)" }}
            >
              Job Discovery
            </p>
            <h2
              className="text-2xl sm:text-4xl font-extrabold tracking-tight"
              style={{ color: "var(--color-text)" }}
            >
              Aggregated & Scored Roles
            </h2>
            <p
              className="mt-2 text-sm sm:text-base max-w-xl leading-relaxed"
              style={{ color: "var(--color-subtle)" }}
            >
              Real-time openings aggregated across premier technical boards, scored against your engineering profile.
            </p>
          </div>

          {/* Filter tabs */}
          <div
            className="flex items-center p-1 rounded-lg border self-start md:self-auto"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
          >
            {[
              { id: "all", label: "All Opportunities" },
              { id: "remoteok", label: "RemoteOK" },
              { id: "yc_jobs", label: "YC Jobs" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className="px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer"
                style={{
                  background: activeTab === tab.id ? "var(--color-surface-hover)" : "transparent",
                  color: activeTab === tab.id ? "var(--color-text)" : "var(--color-subtle)",
                  border: activeTab === tab.id ? "1px solid var(--color-border)" : "1px solid transparent",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </ScrollReveal>

      {/* Stack of interactive job preview cards */}
      <div className="flex flex-col gap-3.5 mb-8">
        {filteredRoles.map((job, idx) => (
          <ScrollReveal
            key={job.id}
            animation="fade-up"
            delayMs={idx * 60}
          >
            <div
              className="p-4 sm:p-5 rounded-xl border card-interactive group"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
              }}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span
                      className="text-[0.6875rem] font-bold uppercase tracking-wider px-2 py-0.5 rounded"
                      style={{
                        background: "var(--color-bg)",
                        color: "var(--color-gold)",
                        border: "1px solid var(--color-border)",
                      }}
                    >
                      {job.sourceLabel}
                    </span>
                    <span className="text-xs" style={{ color: "var(--color-muted)" }}>·</span>
                    <span className="text-xs" style={{ color: "var(--color-muted)" }}>
                      Posted {job.posted}
                    </span>
                  </div>

                  <h3
                    className="font-bold text-base sm:text-lg group-hover:text-[var(--color-gold)] transition-colors"
                    style={{ color: "var(--color-text)" }}
                  >
                    {job.title}
                  </h3>

                  <p className="text-xs sm:text-sm mt-0.5" style={{ color: "var(--color-subtle)" }}>
                    <span className="font-semibold text-[var(--color-text)]">{job.company}</span> · {job.location}
                  </p>

                  {/* Skills pill row */}
                  <div className="flex flex-wrap items-center gap-1.5 mt-3">
                    {job.skills.map((skill) => (
                      <span
                        key={skill}
                        className="px-2 py-0.5 rounded text-[0.7rem] font-medium"
                        style={{
                          background: "var(--color-bg)",
                          color: "var(--color-subtle)",
                          border: "1px solid var(--color-border)",
                        }}
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Score & Status Indicators */}
                <div className="flex items-center gap-2.5 flex-shrink-0 self-start sm:self-auto border-t sm:border-t-0 pt-3 sm:pt-0 w-full sm:w-auto justify-between sm:justify-end">
                  <StatusBadge status={job.status} />
                  <ScoreBadge score={job.score} />
                  <Link href="/dashboard" className="hidden sm:inline-block">
                    <Button size="sm" variant="secondary" className="text-xs">
                      Inspect →
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </ScrollReveal>
        ))}
      </div>

      {/* Explore catalog button */}
      <div className="text-center">
        <Link href="/jobs">
          <Button size="md" variant="secondary" className="gap-2">
            Explore All Aggregated Jobs
            <span>→</span>
          </Button>
        </Link>
      </div>
    </section>
  );
}
