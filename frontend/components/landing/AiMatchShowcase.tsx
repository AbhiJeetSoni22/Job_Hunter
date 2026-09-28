"use client";

import { useState } from "react";
import { ScoreRing, ScrollReveal } from "@/components/ui/Motion";
import { Badge } from "@/components/ui/Badge";
import Link from "next/link";
import { Button } from "@/components/ui/Button";

type ViewMode = "overview" | "matched" | "missing" | "prep";

export function AiMatchShowcase() {
  const [activeView, setActiveView] = useState<ViewMode>("overview");

  return (
    <section id="ai-match" className="py-14 sm:py-24 border-t relative" style={{ borderColor: "var(--color-border)" }}>
      {/* Background ambient radial glow */}
      <div
        aria-hidden="true"
        className="absolute top-1/2 left-0 w-[450px] h-[450px] rounded-full pointer-events-none opacity-25 -z-10"
        style={{
          background: "radial-gradient(circle, rgba(143, 23, 51, 0.35) 0%, rgba(201, 166, 107, 0.08) 50%, transparent 75%)",
          filter: "blur(75px)",
        }}
      />

      <ScrollReveal animation="fade-up">
        <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16">
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border mb-3"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
          >
            <span className="text-xs uppercase tracking-wider font-semibold" style={{ color: "var(--color-gold)" }}>
              Core Intelligence
            </span>
          </div>
          <h2
            className="text-2xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            How AI Evaluates Your Fit
          </h2>
          <p
            className="mt-3 text-sm sm:text-base leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            Gemini AI doesn’t just tally keywords — it reads role requirements against your practical project stack,
            calculating a verified alignment score and pinpointing exact concepts to study before interviews.
          </p>
        </div>
      </ScrollReveal>

      {/* 3-Column Engine Visual Transformation */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        {/* Left 4 Cols: Inputs & Engine Flow */}
        <div className="lg:col-span-4 flex flex-col justify-between space-y-3">
          {/* Step 1: Input Resume */}
          <ScrollReveal animation="slide-right" delayMs={50}>
            <div
              className="p-4 rounded-xl border card-layer-shadow transition-all hover:border-[var(--color-gold)]"
              style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
            >
              <div className="flex items-center gap-3">
                <span className="w-10 h-10 rounded-lg flex items-center justify-center text-lg flex-shrink-0"
                      style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)" }}>
                  📄
                </span>
                <div className="min-w-0">
                  <span className="text-[0.6875rem] font-bold uppercase tracking-wider block" style={{ color: "var(--color-gold)" }}>
                    01 · Candidate Profile
                  </span>
                  <p className="font-bold text-sm truncate" style={{ color: "var(--color-text)" }}>
                    Parsed Technical Resume
                  </p>
                  <p className="text-[0.72rem] mt-0.5 truncate" style={{ color: "var(--color-subtle)" }}>
                    14 verified competencies extracted
                  </p>
                </div>
              </div>
            </div>
          </ScrollReveal>

          {/* Plus connector */}
          <div className="flex justify-center text-xs font-mono font-bold" style={{ color: "var(--color-muted)" }}>
            +
          </div>

          {/* Step 2: Target Role */}
          <ScrollReveal animation="slide-right" delayMs={100}>
            <div
              className="p-4 rounded-xl border card-layer-shadow transition-all hover:border-[var(--color-gold)]"
              style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
            >
              <div className="flex items-center gap-3">
                <span className="w-10 h-10 rounded-lg flex items-center justify-center text-lg flex-shrink-0"
                      style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)" }}>
                  💼
                </span>
                <div className="min-w-0">
                  <span className="text-[0.6875rem] font-bold uppercase tracking-wider block" style={{ color: "var(--color-muted)" }}>
                    02 · Requisition
                  </span>
                  <p className="font-bold text-sm truncate" style={{ color: "var(--color-text)" }}>
                    Role Requirements & Stack
                  </p>
                  <p className="text-[0.72rem] mt-0.5 truncate" style={{ color: "var(--color-subtle)" }}>
                    Software Engineer Intern · RemoteOK
                  </p>
                </div>
              </div>
            </div>
          </ScrollReveal>

          {/* Arrow connector */}
          <div className="flex justify-center text-xs font-mono font-bold" style={{ color: "var(--color-gold)" }}>
            ↓
          </div>

          {/* Step 3: Gemini Evaluation */}
          <ScrollReveal animation="slide-right" delayMs={150}>
            <div
              className="p-4 rounded-xl border card-layer-shadow glow-accent"
              style={{
                background: "linear-gradient(135deg, var(--color-surface) 0%, rgba(143, 23, 51, 0.15) 100%)",
                borderColor: "var(--color-accent-border)",
              }}
            >
              <div className="flex items-center gap-3">
                <span className="w-10 h-10 rounded-lg flex items-center justify-center text-lg flex-shrink-0"
                      style={{ background: "rgba(143, 23, 51, 0.25)", border: "1px solid var(--color-accent-border)" }}>
                  🧠
                </span>
                <div className="min-w-0">
                  <span className="text-[0.6875rem] font-bold uppercase tracking-wider block" style={{ color: "var(--color-gold)" }}>
                    03 · Semantic Analysis
                  </span>
                  <p className="font-bold text-sm truncate" style={{ color: "var(--color-text)" }}>
                    Gemini AI Scoring Engine
                  </p>
                  <p className="text-[0.72rem] mt-0.5 truncate" style={{ color: "var(--color-subtle)" }}>
                    Contextual comparison of depth & gaps
                  </p>
                </div>
              </div>
            </div>
          </ScrollReveal>
        </div>

        {/* Right 8 Cols: Interactive AI Transformation Card */}
        <div className="lg:col-span-8">
          <ScrollReveal animation="fade-up" delayMs={100} className="h-full">
            <div
              className="p-6 sm:p-8 rounded-2xl border card-layer-shadow h-full flex flex-col justify-between spotlight-card"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
              }}
            >
              <div>
                {/* Header with Title and Score Ring */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b"
                     style={{ borderColor: "var(--color-border)" }}>
                  <div>
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--color-gold)" }}>
                        AI Match Intelligence
                      </span>
                      <span className="text-xs" style={{ color: "var(--color-muted)" }}>·</span>
                      <Badge color="green">High Alignment</Badge>
                      <span
                        className="text-[0.625rem] font-semibold uppercase tracking-wider px-2 py-0.5 rounded border ml-1"
                        style={{
                          background: "var(--color-bg)",
                          borderColor: "var(--color-border)",
                          color: "var(--color-muted)",
                        }}
                      >
                        Illustrative Demo
                      </span>
                    </div>

                    <h3 className="font-bold text-lg sm:text-2xl" style={{ color: "var(--color-text)" }}>
                      Full-Stack Engineer Intern
                    </h3>
                    <p className="text-xs sm:text-sm mt-0.5" style={{ color: "var(--color-subtle)" }}>
                      <span className="font-semibold text-[var(--color-text)]">Sample: Corelogic</span> · San Francisco, CA · RemoteOK
                    </p>
                  </div>

                  <div className="flex items-center gap-3 self-start sm:self-auto flex-shrink-0">
                    <ScoreRing score={88} size="lg" showLabel />
                  </div>
                </div>

                {/* View Switcher Tabs */}
                <div
                  className="flex items-center p-1 rounded-lg border mt-5 text-xs overflow-x-auto"
                  style={{
                    background: "var(--color-bg)",
                    borderColor: "var(--color-border)",
                  }}
                >
                  {[
                    { id: "overview", label: "Fit Overview" },
                    { id: "matched", label: "Verified Matches (5)" },
                    { id: "missing", label: "Skill Gaps (2)" },
                    { id: "prep", label: "Interview Readiness" },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setActiveView(tab.id as ViewMode)}
                      className="flex-1 py-1.5 px-2.5 rounded-md font-medium text-center whitespace-nowrap transition-all cursor-pointer"
                      style={{
                        background: activeView === tab.id ? "var(--color-surface)" : "transparent",
                        color: activeView === tab.id ? "var(--color-text)" : "var(--color-muted)",
                        border: activeView === tab.id ? "1px solid var(--color-border)" : "1px solid transparent",
                      }}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Dynamic Content Panel */}
                <div className="mt-4 min-h-[140px]">
                  {activeView === "overview" && (
                    <div
                      className="p-4 rounded-xl text-xs sm:text-sm leading-relaxed"
                      style={{
                        background: "var(--color-bg)",
                        border: "1px solid var(--color-border)",
                        color: "var(--color-text)",
                      }}
                    >
                      <span className="font-bold block mb-1 text-[var(--color-gold)]">
                        Gemini Semantic Assessment:
                      </span>
                      Candidate demonstrates strong practical proficiency in React, TypeScript, and REST APIs,
                      fulfilling 88% of core technical competencies. Candidate’s recent full-stack project
                      proves client architecture capabilities. Recommendation: review PostgreSQL indexing
                      and containerized deployments prior to technical screening.
                    </div>
                  )}

                  {activeView === "matched" && (
                    <div
                      className="p-4 rounded-xl"
                      style={{ background: "rgba(34, 197, 94, 0.05)", border: "1px solid rgba(34, 197, 94, 0.2)" }}
                    >
                      <p className="text-[0.7rem] font-bold uppercase tracking-wider mb-2.5" style={{ color: "var(--color-green)" }}>
                        ✓ Directly Fulfills Primary Job Requirements (5)
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {["React 19", "TypeScript", "Node.js", "REST APIs", "Git Workflow"].map((s) => (
                          <span
                            key={s}
                            className="px-2.5 py-1 rounded text-xs font-medium"
                            style={{
                              background: "rgba(34, 197, 94, 0.12)",
                              color: "var(--color-green)",
                              border: "1px solid rgba(34, 197, 94, 0.3)",
                            }}
                          >
                            ✓ {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {activeView === "missing" && (
                    <div
                      className="p-4 rounded-xl"
                      style={{ background: "rgba(234, 179, 8, 0.05)", border: "1px solid rgba(234, 179, 8, 0.2)" }}
                    >
                      <p className="text-[0.7rem] font-bold uppercase tracking-wider mb-2.5" style={{ color: "var(--color-amber)" }}>
                        ! Concepts to Review Before Technical Interview (2)
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {["Docker Containerization", "PostgreSQL Indexing"].map((s) => (
                          <span
                            key={s}
                            className="px-2.5 py-1 rounded text-xs font-medium"
                            style={{
                              background: "rgba(234, 179, 8, 0.12)",
                              color: "var(--color-amber)",
                              border: "1px solid rgba(234, 179, 8, 0.3)",
                            }}
                          >
                            ! {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {activeView === "prep" && (
                    <div
                      className="p-4 rounded-xl text-xs space-y-2"
                      style={{
                        background: "var(--color-bg)",
                        border: "1px solid var(--color-border)",
                      }}
                    >
                      <p className="font-bold text-[var(--color-gold)]">
                        Role-Specific Screening Questions:
                      </p>
                      <div className="p-2.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-subtle)]">
                        &quot;How do you optimize React render cycles and state synchronization in a high-frequency dashboard?&quot;
                      </div>
                      <div className="p-2.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-subtle)]">
                        &quot;Explain the trade-offs between B-tree indexes and hash indexes in PostgreSQL.&quot;
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Bottom Card Footer */}
              <div
                className="mt-6 pt-4 border-t flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs"
                style={{ borderColor: "var(--color-border)" }}
              >
                <div className="flex items-center gap-2">
                  <span style={{ color: "var(--color-muted)" }}>Targeted Prep Engine:</span>
                  <span className="font-semibold" style={{ color: "var(--color-gold)" }}>
                    Available On Demand
                  </span>
                </div>
                <Link href="/jobs">
                  <Button size="sm" variant="secondary" className="text-xs">
                    Inspect in Job Catalog →
                  </Button>
                </Link>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </div>
    </section>
  );
}
