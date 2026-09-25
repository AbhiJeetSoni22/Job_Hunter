"use client";

import { ScrollReveal } from "@/components/ui/Motion";
import { ScoreBadge } from "@/components/jobs/ScoreBadge";
import { StatusBadge } from "@/components/jobs/StatusBadge";
import Link from "next/link";
import { Button } from "@/components/ui/Button";

export function DashboardShowcase() {
  return (
    <section className="py-12 sm:py-20 border-t" style={{ borderColor: "var(--color-border)" }}>
      <ScrollReveal animation="fade-up">
        <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16">
          <p
            className="text-xs uppercase tracking-wider font-semibold mb-2"
            style={{ color: "var(--color-gold)" }}
          >
            Product Interface
          </p>
          <h2
            className="text-2xl sm:text-4xl font-extrabold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            Your Daily Job-Hunting Command Center
          </h2>
          <p
            className="mt-3 text-sm sm:text-base leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            All critical metrics, match distributions, and action items accessible from a unified dashboard.
          </p>
        </div>
      </ScrollReveal>

      {/* Realistic Product Mockup Container */}
      <ScrollReveal animation="fade-up" delayMs={100}>
        <div
          className="rounded-2xl border overflow-hidden card-elevated glow-accent max-w-5xl mx-auto"
          style={{
            background: "var(--color-bg)",
            borderColor: "var(--color-border)",
          }}
        >
          {/* Mock Browser/App Header Bar */}
          <div
            className="flex items-center justify-between px-4 sm:px-6 py-3 border-b"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
          >
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500/40 inline-block" />
              <span className="w-3 h-3 rounded-full bg-yellow-500/40 inline-block" />
              <span className="w-3 h-3 rounded-full bg-green-500/40 inline-block" />
              <span className="ml-3 font-mono text-xs hidden sm:inline-block" style={{ color: "var(--color-muted)" }}>
                job-hunter.app/dashboard
              </span>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <span className="w-2 h-2 rounded-full" style={{ background: "var(--color-green)" }} />
              <span style={{ color: "var(--color-subtle)" }}>AI Engine Ready</span>
            </div>
          </div>

          {/* Internal Dashboard View */}
          <div className="p-4 sm:p-7 space-y-6">
            {/* Top row: Welcome + Live Sync status */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2">
              <div>
                <h3 className="font-extrabold text-lg sm:text-xl" style={{ color: "var(--color-text)" }}>
                  Good morning, Engineer
                </h3>
                <p className="text-xs sm:text-sm mt-0.5" style={{ color: "var(--color-subtle)" }}>
                  Here are the opportunities worth looking at today.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className="px-3 py-1 rounded-md text-xs font-medium"
                  style={{
                    background: "var(--color-surface)",
                    color: "var(--color-text)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  🔄 Synced 12m ago
                </span>
              </div>
            </div>

            {/* 4 Stat Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
              {[
                { label: "Total Jobs", val: "164", sub: "RemoteOK + YC", icon: "💼" },
                { label: "Scored Jobs", val: "142", sub: "Evaluated by AI", icon: "🧮" },
                { label: "Top Match", val: "95%", sub: "Vectra AI", icon: "🏆", color: "var(--color-green)" },
                { label: "Applications", val: "12", sub: "In Pipeline", icon: "📨", color: "var(--color-sky)" },
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
                    {s.val}
                  </p>
                  <p className="text-[0.72rem] mt-0.5" style={{ color: "var(--color-subtle)" }}>
                    {s.sub}
                  </p>
                </div>
              ))}
            </div>

            {/* Split row: Top Matches & Match Quality */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              {/* Left 7 cols: Top Matches list */}
              <div
                className="lg:col-span-8 p-4 sm:p-5 rounded-xl border"
                style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
              >
                <div className="flex items-center justify-between mb-4 pb-2 border-b" style={{ borderColor: "var(--color-border)" }}>
                  <span className="font-bold text-sm" style={{ color: "var(--color-text)" }}>
                    ⭐ Top Recommendations
                  </span>
                  <span className="text-[0.6875rem] uppercase tracking-wider font-semibold" style={{ color: "var(--color-muted)" }}>
                    Ranked by AI Fit
                  </span>
                </div>

                <div className="space-y-2.5">
                  {[
                    { role: "Frontend Engineer Intern", co: "Vectra AI", score: 95, status: "applied" as const },
                    { role: "Full-Stack Development Intern", co: "Nimbus Labs", score: 91, status: "interview" as const },
                    { role: "Software Engineer Intern", co: "Corelogic", score: 88, status: "saved" as const },
                  ].map((job) => (
                    <div
                      key={job.co}
                      className="p-3 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
                      style={{ background: "var(--color-bg)", borderColor: "var(--color-border)" }}
                    >
                      <div>
                        <p className="font-semibold" style={{ color: "var(--color-text)" }}>
                          {job.role}
                        </p>
                        <p className="mt-0.5" style={{ color: "var(--color-subtle)" }}>
                          {job.co}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 self-start sm:self-auto">
                        <StatusBadge status={job.status} />
                        <ScoreBadge score={job.score} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right 4 cols: Match Quality Breakdown */}
              <div
                className="lg:col-span-4 p-4 sm:p-5 rounded-xl border flex flex-col justify-between"
                style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
              >
                <div>
                  <div className="flex items-center justify-between mb-4 pb-2 border-b" style={{ borderColor: "var(--color-border)" }}>
                    <span className="font-bold text-sm" style={{ color: "var(--color-text)" }}>
                      Quality Breakdown
                    </span>
                    <span className="text-[0.6875rem] uppercase tracking-wider font-semibold" style={{ color: "var(--color-muted)" }}>
                      142 Scored
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 mb-4">
                    <div className="p-2.5 rounded-lg text-center" style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)" }}>
                      <p className="text-base font-bold" style={{ color: "var(--color-green)" }}>24</p>
                      <p className="text-[0.6875rem] font-semibold mt-0.5" style={{ color: "var(--color-text)" }}>Excellent</p>
                      <p className="text-[0.625rem]" style={{ color: "var(--color-muted)" }}>90–100%</p>
                    </div>
                    <div className="p-2.5 rounded-lg text-center" style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)" }}>
                      <p className="text-base font-bold" style={{ color: "var(--color-sky)" }}>48</p>
                      <p className="text-[0.6875rem] font-semibold mt-0.5" style={{ color: "var(--color-text)" }}>Good</p>
                      <p className="text-[0.625rem]" style={{ color: "var(--color-muted)" }}>75–89%</p>
                    </div>
                  </div>
                </div>

                <Link href="/dashboard" className="w-full">
                  <Button size="sm" variant="secondary" className="w-full text-xs">
                    Open Full Cockpit →
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
