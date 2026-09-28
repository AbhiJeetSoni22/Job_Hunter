"use client";

import { useState } from "react";
import { ScrollReveal, ScoreRing, AnimatedCounter } from "@/components/ui/Motion";
import { ScoreBadge } from "@/components/jobs/ScoreBadge";
import { StatusBadge } from "@/components/jobs/StatusBadge";
import Link from "next/link";
import { Button } from "@/components/ui/Button";

interface CockpitJob {
  id: string;
  role: string;
  co: string;
  score: number;
  status: "applied" | "interview" | "saved";
  source: string;
  reason: string;
  matchedSkills: string[];
}

const COCKPIT_ROLES: CockpitJob[] = [
  {
    id: "1",
    role: "Frontend Engineer Intern",
    co: "Sample: Vectra AI",
    score: 95,
    status: "applied",
    source: "RemoteOK",
    reason: "Direct match on React 19, TypeScript, and client-side performance.",
    matchedSkills: ["React", "TypeScript", "TailwindCSS"],
  },
  {
    id: "2",
    role: "Full-Stack Development Intern",
    co: "Sample: Nimbus Labs",
    score: 91,
    status: "interview",
    source: "YC Jobs",
    reason: "Node.js and REST architectures fulfill team core product requirements.",
    matchedSkills: ["Node.js", "REST APIs", "PostgreSQL"],
  },
  {
    id: "3",
    role: "Software Engineer Intern",
    co: "Sample: Corelogic",
    score: 88,
    status: "saved",
    source: "RemoteOK",
    reason: "Candidate’s project stack closely matches full-stack requirements.",
    matchedSkills: ["TypeScript", "FastAPI", "Docker"],
  },
];

export function DashboardShowcase() {
  const [selectedJob, setSelectedJob] = useState<CockpitJob>(COCKPIT_ROLES[0]);

  return (
    <section id="cockpit" className="py-14 sm:py-24 border-t relative" style={{ borderColor: "var(--color-border)" }}>
      {/* Background ambient radial glow */}
      <div
        aria-hidden="true"
        className="absolute top-1/2 right-1/4 w-[500px] h-[500px] rounded-full pointer-events-none opacity-25 -z-10"
        style={{
          background: "radial-gradient(circle, rgba(143, 23, 51, 0.3) 0%, rgba(201, 166, 107, 0.08) 50%, transparent 75%)",
          filter: "blur(80px)",
        }}
      />

      <ScrollReveal animation="fade-up">
        <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16">
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border mb-3"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
          >
            <span className="text-xs uppercase tracking-wider font-semibold" style={{ color: "var(--color-gold)" }}>
              Product Interface
            </span>
          </div>
          <h2
            className="text-2xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            Your Daily Job-Hunting Command Center
          </h2>
          <p
            className="mt-3 text-sm sm:text-base leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            All critical metrics, match distributions, and action items accessible from a unified cockpit.
          </p>
        </div>
      </ScrollReveal>

      {/* Living Interactive Product Mockup */}
      <ScrollReveal animation="scale-in" delayMs={80}>
        <div
          className="rounded-2xl border overflow-hidden card-layer-shadow max-w-5xl mx-auto"
          style={{
            background: "var(--color-bg)",
            borderColor: "var(--color-border)",
          }}
        >
          {/* App Window Chrome Header Bar */}
          <div
            className="flex items-center justify-between px-4 sm:px-6 py-3 border-b"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
          >
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/50 inline-block" />
              <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/50 inline-block" />
              <span className="w-2.5 h-2.5 rounded-full bg-green-500/50 inline-block" />
              <span className="ml-3 font-mono text-xs hidden sm:inline-block" style={{ color: "var(--color-muted)" }}>
                job-hunter.app/dashboard
              </span>
            </div>

            <div className="flex items-center gap-3">
              <span
                className="text-[0.625rem] font-bold uppercase tracking-wider px-2 py-0.5 rounded border"
                style={{
                  background: "var(--color-bg)",
                  borderColor: "var(--color-border)",
                  color: "var(--color-gold)",
                }}
              >
                Interactive Cockpit Demo
              </span>
              <div className="flex items-center gap-1.5 text-xs">
                <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "var(--color-green)" }} />
                <span className="hidden sm:inline" style={{ color: "var(--color-subtle)" }}>AI Engine Ready</span>
              </div>
            </div>
          </div>

          {/* Cockpit Content */}
          <div className="p-4 sm:p-7 space-y-6">
            {/* Top Greeting & Scraper Sync Pill */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b"
                 style={{ borderColor: "var(--color-border)" }}>
              <div>
                <h3 className="font-extrabold text-lg sm:text-xl" style={{ color: "var(--color-text)" }}>
                  Good morning, Engineer
                </h3>
                <p className="text-xs sm:text-sm mt-0.5" style={{ color: "var(--color-subtle)" }}>
                  Here are the verified technical opportunities ranked for you today.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className="px-3 py-1 rounded-lg text-xs font-medium border"
                  style={{
                    background: "var(--color-surface)",
                    color: "var(--color-gold)",
                    borderColor: "var(--color-border)",
                  }}
                >
                  🔄 Scrapers Synced Today
                </span>
              </div>
            </div>

            {/* 4 Animated Stat Counters */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
              {[
                { label: "Total Openings", count: 164, suffix: "", sub: "RemoteOK + YC", icon: "💼" },
                { label: "AI Scored Roles", count: 142, suffix: "", sub: "Semantic Evaluation", icon: "🧮" },
                { label: "Top Match", count: 95, suffix: "%", sub: "Vectra AI", icon: "🏆", color: "var(--color-green)" },
                { label: "In Pipeline", count: 12, suffix: " Active", sub: "Saved to Offer", icon: "📨", color: "var(--color-sky)" },
              ].map((s) => (
                <div
                  key={s.label}
                  className="p-3.5 sm:p-4 rounded-xl border"
                  style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
                >
                  <div className="flex items-center justify-between text-xs mb-1" style={{ color: "var(--color-muted)" }}>
                    <span className="uppercase tracking-wider font-semibold text-[0.6875rem]">{s.label}</span>
                    <span>{s.icon}</span>
                  </div>
                  <p
                    className="text-xl sm:text-2xl font-black"
                    style={{ color: s.color ?? "var(--color-text)" }}
                  >
                    <AnimatedCounter value={s.count} suffix={s.suffix} durationMs={700} />
                  </p>
                  <p className="text-[0.72rem] mt-0.5" style={{ color: "var(--color-subtle)" }}>
                    {s.sub}
                  </p>
                </div>
              ))}
            </div>

            {/* Interactive Split View: Clickable Top Matches + Live Inspector */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              {/* Left 7 cols: Selectable Top Matches */}
              <div
                className="lg:col-span-7 p-4 sm:p-5 rounded-xl border flex flex-col justify-between"
                style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
              >
                <div>
                  <div className="flex items-center justify-between mb-3 pb-2 border-b" style={{ borderColor: "var(--color-border)" }}>
                    <span className="font-bold text-sm" style={{ color: "var(--color-text)" }}>
                      ⭐ Top Recommendations
                    </span>
                    <span className="text-[0.6875rem] uppercase tracking-wider font-semibold" style={{ color: "var(--color-muted)" }}>
                      Click to Inspect
                    </span>
                  </div>

                  <div className="space-y-2">
                    {COCKPIT_ROLES.map((job) => {
                      const isSelected = selectedJob.id === job.id;
                      return (
                        <div
                          key={job.id}
                          role="button"
                          tabIndex={0}
                          onClick={() => setSelectedJob(job)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              setSelectedJob(job);
                            }
                          }}
                          className="p-3 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs cursor-pointer transition-all"
                          style={{
                            background: isSelected ? "var(--color-surface-hover)" : "var(--color-bg)",
                            borderColor: isSelected ? "var(--color-gold)" : "var(--color-border)",
                            boxShadow: isSelected ? "0 0 12px rgba(201, 166, 107, 0.15)" : "none",
                          }}
                        >
                          <div>
                            <div className="flex items-center gap-1.5 mb-0.5">
                              <span className="font-semibold text-sm" style={{ color: "var(--color-text)" }}>
                                {job.role}
                              </span>
                              {isSelected && (
                                <span className="text-[0.625rem] px-1.5 py-0.2 rounded bg-[var(--color-gold-subtle)] text-[var(--color-gold)] font-bold">
                                  ACTIVE
                                </span>
                              )}
                            </div>
                            <p style={{ color: "var(--color-subtle)" }}>
                              {job.co} · {job.source}
                            </p>
                          </div>

                          <div className="flex items-center gap-2 self-start sm:self-auto flex-shrink-0">
                            <StatusBadge status={job.status} />
                            <ScoreBadge score={job.score} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t text-[0.7rem] text-[var(--color-muted)] flex justify-between items-center">
                  <span>Selected: {selectedJob.role}</span>
                  <Link href="/dashboard" className="text-[var(--color-gold)] hover:underline font-semibold">
                    Launch Full Cockpit →
                  </Link>
                </div>
              </div>

              {/* Right 5 cols: Live Inspector & Quality Breakdown */}
              <div
                className="lg:col-span-5 p-4 sm:p-5 rounded-xl border flex flex-col justify-between"
                style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
              >
                <div>
                  <div className="flex items-center justify-between mb-3 pb-2 border-b" style={{ borderColor: "var(--color-border)" }}>
                    <span className="font-bold text-sm" style={{ color: "var(--color-text)" }}>
                      AI Inspector Details
                    </span>
                    <span className="text-[0.6875rem] font-bold text-[var(--color-gold)]">
                      {selectedJob.score}% Match
                    </span>
                  </div>

                  <div className="p-3 rounded-lg border mb-4 text-xs"
                       style={{ background: "var(--color-bg)", borderColor: "var(--color-border)" }}>
                    <p className="font-semibold text-[var(--color-gold)] mb-1">
                      {selectedJob.role} @ {selectedJob.co}
                    </p>
                    <p className="text-[var(--color-subtle)] leading-relaxed">
                      {selectedJob.reason}
                    </p>
                    <div className="flex flex-wrap gap-1 mt-2.5">
                      {selectedJob.matchedSkills.map((s) => (
                        <span key={s} className="px-2 py-0.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[0.6875rem] text-[var(--color-green)]">
                          ✓ {s}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Match Quality Breakdown stats */}
                  <span className="font-bold text-xs uppercase tracking-wider block mb-2" style={{ color: "var(--color-muted)" }}>
                    Score Quality Distribution
                  </span>
                  <div className="grid grid-cols-2 gap-2 text-xs text-center">
                    <div className="p-2 rounded-lg border" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)" }}>
                      <p className="font-black text-sm text-[var(--color-green)]">24</p>
                      <p className="text-[0.6875rem] font-semibold text-[var(--color-text)]">Excellent</p>
                      <p className="text-[0.625rem] text-[var(--color-muted)]">≥ 90%</p>
                    </div>
                    <div className="p-2 rounded-lg border" style={{ background: "var(--color-bg)", borderColor: "var(--color-border)" }}>
                      <p className="font-black text-sm text-[var(--color-sky)]">48</p>
                      <p className="text-[0.6875rem] font-semibold text-[var(--color-text)]">Good</p>
                      <p className="text-[0.625rem] text-[var(--color-muted)]">75–89%</p>
                    </div>
                  </div>
                </div>

                <Link href="/dashboard" className="w-full mt-4">
                  <Button size="sm" variant="secondary" className="w-full text-xs font-semibold btn-fx">
                    Open Your Full Cockpit →
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </ScrollReveal>
    </section>
  );
}
