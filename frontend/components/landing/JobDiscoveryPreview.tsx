"use client";

import { useState } from "react";
import Link from "next/link";
import { ScrollReveal } from "@/components/ui/Motion";
import { ScoreBadge } from "@/components/jobs/ScoreBadge";
import { StatusBadge } from "@/components/jobs/StatusBadge";
import { Button } from "@/components/ui/Button";

interface SampleJob {
  id: string;
  title: string;
  company: string;
  location: string;
  source: "remoteok" | "yc_jobs";
  sourceLabel: string;
  score: number;
  status: "applied" | "saved" | "interview";
  skills: string[];
  posted: string;
  aiInsight: string;
  featured?: boolean;
}

const SAMPLE_ROLES: SampleJob[] = [
  {
    id: "1",
    title: "Software Engineer Intern (Frontend)",
    company: "Sample: Vectra AI",
    location: "Remote / New York",
    source: "remoteok",
    sourceLabel: "RemoteOK",
    score: 95,
    status: "applied",
    skills: ["React", "TypeScript", "TailwindCSS", "Next.js"],
    posted: "1d ago",
    aiInsight: "Candidate matches 95% of required frontend stack. High proficiency in React component lifecycle.",
    featured: true,
  },
  {
    id: "2",
    title: "Full-Stack Development Intern",
    company: "Sample: Helios Dynamics",
    location: "San Francisco, CA",
    source: "yc_jobs",
    sourceLabel: "YC Jobs",
    score: 87,
    status: "saved",
    skills: ["TypeScript", "Node.js", "PostgreSQL", "FastAPI"],
    posted: "2d ago",
    aiInsight: "Strong backend framework match. Recommend reviewing PostgreSQL indexing.",
  },
  {
    id: "3",
    title: "AI Platform & Engineering Intern",
    company: "Sample: Synthesis Cloud",
    location: "Remote / London",
    source: "remoteok",
    sourceLabel: "RemoteOK",
    score: 82,
    status: "interview",
    skills: ["Python", "PyTorch", "Docker", "REST APIs"],
    posted: "3d ago",
    aiInsight: "Direct match for Python and REST APIs. PyTorch projects fulfill core criteria.",
  },
];

export function JobDiscoveryPreview() {
  const [activeTab, setActiveTab] = useState<"all" | "remoteok" | "yc_jobs">("all");

  const filteredRoles =
    activeTab === "all"
      ? SAMPLE_ROLES
      : SAMPLE_ROLES.filter((r) => r.source === activeTab);

  const featuredJob = filteredRoles.find((r) => r.featured) ?? filteredRoles[0];
  const supportingJobs = filteredRoles.filter((r) => r.id !== featuredJob?.id);

  return (
    <section id="discovery" className="py-14 sm:py-24 border-t relative" style={{ borderColor: "var(--color-border)" }}>
      <ScrollReveal animation="fade-up">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div>
            <div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full border mb-3"
              style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
            >
              <span className="text-xs uppercase tracking-wider font-semibold" style={{ color: "var(--color-gold)" }}>
                Job Discovery
              </span>
              <span className="text-xs" style={{ color: "var(--color-muted)" }}>·</span>
              <span className="text-[0.6875rem] font-semibold text-[var(--color-muted)]">
                Sample Catalog Feed
              </span>
            </div>
            <h2
              className="text-2xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight"
              style={{ color: "var(--color-text)" }}
            >
              Aggregated & Scored Roles
            </h2>
            <p
              className="mt-3 text-sm sm:text-base max-w-xl leading-relaxed"
              style={{ color: "var(--color-subtle)" }}
            >
              Real-time openings aggregated across premier technical boards, ranked directly by your profile compatibility.
            </p>
          </div>

          {/* Filter tabs */}
          <div
            className="flex items-center p-1 rounded-xl border self-start md:self-auto"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
          >
            {[
              { id: "all", label: "All Sources" },
              { id: "remoteok", label: "RemoteOK" },
              { id: "yc_jobs", label: "YC Jobs" },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className="px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer"
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

      {/* Asymmetric Tiered Composition: Featured Job + Supporting Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-10">
        {/* Featured Primary Job Card (7 cols) */}
        {featuredJob && (
          <div className="lg:col-span-7">
            <ScrollReveal animation="fade-up" delayMs={50} className="h-full">
              <div
                className="p-6 sm:p-7 rounded-2xl border card-layer-shadow h-full flex flex-col justify-between spotlight-card"
                style={{
                  background: "var(--color-surface)",
                  borderColor: "rgba(201, 166, 107, 0.3)",
                }}
              >
                <div>
                  <div className="flex items-center justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2">
                      <span
                        className="text-[0.6875rem] font-bold uppercase tracking-wider px-2 py-0.5 rounded border"
                        style={{
                          background: "var(--color-bg)",
                          color: "var(--color-gold)",
                          borderColor: "var(--color-border)",
                        }}
                      >
                        {featuredJob.sourceLabel}
                      </span>
                      <span className="text-xs" style={{ color: "var(--color-muted)" }}>
                        Posted {featuredJob.posted}
                      </span>
                    </div>

                    <span
                      className="text-[0.625rem] font-bold uppercase tracking-wider px-2 py-0.5 rounded"
                      style={{
                        background: "rgba(143, 23, 51, 0.15)",
                        color: "var(--color-gold)",
                        border: "1px solid var(--color-accent-border)",
                      }}
                    >
                      ★ Top Opportunity
                    </span>
                  </div>

                  <h3 className="font-bold text-lg sm:text-2xl" style={{ color: "var(--color-text)" }}>
                    {featuredJob.title}
                  </h3>
                  <p className="text-xs sm:text-sm mt-1" style={{ color: "var(--color-subtle)" }}>
                    <span className="font-semibold text-[var(--color-text)]">{featuredJob.company}</span> · {featuredJob.location}
                  </p>

                  {/* AI Insight Box */}
                  <div
                    className="mt-4 p-3.5 rounded-xl border text-xs leading-relaxed"
                    style={{
                      background: "var(--color-bg-subtle)",
                      borderColor: "var(--color-border)",
                    }}
                  >
                    <span className="font-semibold block mb-0.5" style={{ color: "var(--color-gold)" }}>
                      AI Match Assessment
                    </span>
                    <p style={{ color: "var(--color-subtle)" }}>
                      {featuredJob.aiInsight}
                    </p>
                  </div>

                  {/* Required Tech Stack */}
                  <div className="mt-4">
                    <p className="text-[0.6875rem] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-muted)" }}>
                      Matched Technologies
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {featuredJob.skills.map((skill) => (
                        <span
                          key={skill}
                          className="px-2 py-0.5 rounded text-xs font-medium"
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
                </div>

                {/* Bottom Action Footer */}
                <div
                  className="mt-6 pt-4 border-t flex items-center justify-between gap-3"
                  style={{ borderColor: "var(--color-border)" }}
                >
                  <div className="flex items-center gap-2">
                    <StatusBadge status={featuredJob.status} />
                    <ScoreBadge score={featuredJob.score} />
                  </div>

                  <Link href="/jobs">
                    <Button size="sm" className="btn-fx text-xs font-semibold">
                      Inspect Details →
                    </Button>
                  </Link>
                </div>
              </div>
            </ScrollReveal>
          </div>
        )}

        {/* Supporting Job Cards (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          {supportingJobs.map((job, idx) => (
            <ScrollReveal key={job.id} animation="fade-up" delayMs={idx * 80} className="h-full">
              <div
                className="p-5 rounded-xl border card-layer-shadow flex flex-col justify-between h-full spotlight-card"
                style={{
                  background: "var(--color-surface)",
                  borderColor: "var(--color-border)",
                }}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span
                      className="text-[0.6875rem] font-bold uppercase tracking-wider px-2 py-0.5 rounded border"
                      style={{
                        background: "var(--color-bg)",
                        color: "var(--color-gold)",
                        borderColor: "var(--color-border)",
                      }}
                    >
                      {job.sourceLabel}
                    </span>
                    <span className="text-xs" style={{ color: "var(--color-muted)" }}>
                      Posted {job.posted}
                    </span>
                  </div>

                  <h3 className="font-bold text-base sm:text-lg leading-snug" style={{ color: "var(--color-text)" }}>
                    {job.title}
                  </h3>
                  <p className="text-xs mt-1" style={{ color: "var(--color-subtle)" }}>
                    <span className="font-semibold text-[var(--color-text)]">{job.company}</span> · {job.location}
                  </p>

                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {job.skills.map((skill) => (
                      <span
                        key={skill}
                        className="px-2 py-0.5 rounded text-[0.7rem] font-medium"
                        style={{
                          background: "var(--color-bg)",
                          color: "var(--color-muted)",
                          border: "1px solid var(--color-border)",
                        }}
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                <div
                  className="mt-4 pt-3 border-t flex items-center justify-between"
                  style={{ borderColor: "var(--color-border)" }}
                >
                  <div className="flex items-center gap-2">
                    <StatusBadge status={job.status} />
                    <ScoreBadge score={job.score} />
                  </div>
                  <Link href="/jobs" className="text-xs font-semibold hover:underline" style={{ color: "var(--color-gold)" }}>
                    View Role →
                  </Link>
                </div>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>

      {/* Catalog CTA */}
      <div className="text-center mt-6">
        <Link href="/jobs">
          <Button size="md" variant="secondary" className="gap-2 btn-fx">
            <span>Explore All Aggregated Jobs</span>
            <span>→</span>
          </Button>
        </Link>
      </div>
    </section>
  );
}
