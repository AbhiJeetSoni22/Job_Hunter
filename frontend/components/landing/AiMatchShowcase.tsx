"use client";

import { ScoreRing, ScrollReveal } from "@/components/ui/Motion";
import { Badge } from "@/components/ui/Badge";
import Link from "next/link";
import { Button } from "@/components/ui/Button";

export function AiMatchShowcase() {
  return (
    <section className="py-12 sm:py-20 border-t" style={{ borderColor: "var(--color-border)" }}>
      <ScrollReveal animation="fade-up">
        <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16">
          <p
            className="text-xs uppercase tracking-wider font-semibold mb-2"
            style={{ color: "var(--color-gold)" }}
          >
            Core Intelligence
          </p>
          <h2
            className="text-2xl sm:text-4xl font-extrabold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            How AI Evaluates Your Fit
          </h2>
          <p
            className="mt-3 text-sm sm:text-base leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            Gemini AI doesn’t just match keywords — it reads role requirements against your practical project stack, calculating an exact score and identifying areas to prepare before you interview.
          </p>
        </div>
      </ScrollReveal>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-stretch">
        {/* Left Column: Conceptual Evaluation Pipeline */}
        <div className="lg:col-span-4 flex flex-col justify-between space-y-3.5">
          <ScrollReveal animation="fade-up" delayMs={50}>
            <div
              className="p-4 rounded-xl border card-interactive"
              style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
            >
              <div className="flex items-center gap-3">
                <span className="p-2 rounded-lg text-lg" style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)" }}>
                  📄
                </span>
                <div>
                  <p className="text-[0.6875rem] uppercase tracking-wider font-semibold" style={{ color: "var(--color-muted)" }}>
                    Step 1 · Input
                  </p>
                  <p className="font-bold text-sm" style={{ color: "var(--color-text)" }}>
                    Parsed Resume
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--color-subtle)" }}>
                    14 technical skills extracted via Gemini
                  </p>
                </div>
              </div>
            </div>
          </ScrollReveal>

          {/* Connector arrow */}
          <div className="flex justify-center text-xs" style={{ color: "var(--color-muted)" }}>
            ↓
          </div>

          <ScrollReveal animation="fade-up" delayMs={100}>
            <div
              className="p-4 rounded-xl border card-interactive glow-accent"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-accent-border)",
              }}
            >
              <div className="flex items-center gap-3">
                <span className="p-2 rounded-lg text-lg" style={{ background: "rgba(143, 23, 51, 0.2)", border: "1px solid var(--color-accent-border)" }}>
                  🧠
                </span>
                <div>
                  <p className="text-[0.6875rem] uppercase tracking-wider font-semibold" style={{ color: "var(--color-gold)" }}>
                    Step 2 · Engine
                  </p>
                  <p className="font-bold text-sm" style={{ color: "var(--color-text)" }}>
                    Gemini AI Scoring Engine
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--color-subtle)" }}>
                    Contextual comparison of requirements vs projects
                  </p>
                </div>
              </div>
            </div>
          </ScrollReveal>

          {/* Connector arrow */}
          <div className="flex justify-center text-xs" style={{ color: "var(--color-muted)" }}>
            ↓
          </div>

          <ScrollReveal animation="fade-up" delayMs={150}>
            <div
              className="p-4 rounded-xl border card-interactive"
              style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
            >
              <div className="flex items-center gap-3">
                <span className="p-2 rounded-lg text-lg" style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)" }}>
                  💼
                </span>
                <div>
                  <p className="text-[0.6875rem] uppercase tracking-wider font-semibold" style={{ color: "var(--color-muted)" }}>
                    Step 3 · Job Listing
                  </p>
                  <p className="font-bold text-sm" style={{ color: "var(--color-text)" }}>
                    Target Role Requirements
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--color-subtle)" }}>
                    Software Engineer Intern · Corelogic
                  </p>
                </div>
              </div>
            </div>
          </ScrollReveal>
        </div>

        {/* Right Column: Realistic Live AI Match Result Card */}
        <div className="lg:col-span-8">
          <ScrollReveal animation="fade-up" delayMs={150} className="h-full">
            <div
              className="p-6 sm:p-7 rounded-xl border card-elevated h-full flex flex-col justify-between"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
              }}
            >
              {/* Header row */}
              <div>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b"
                     style={{ borderColor: "var(--color-border)" }}
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--color-gold)" }}>
                        AI Score Analysis
                      </span>
                      <span className="text-xs" style={{ color: "var(--color-muted)" }}>·</span>
                      <Badge color="green">Cached Result</Badge>
                    </div>
                    <h3 className="font-bold text-lg sm:text-xl" style={{ color: "var(--color-text)" }}>
                      Full-Stack Engineer Intern
                    </h3>
                    <p className="text-xs sm:text-sm mt-0.5" style={{ color: "var(--color-subtle)" }}>
                      Corelogic · San Francisco, CA · RemoteOK
                    </p>
                  </div>

                  <div className="flex items-center gap-3 flex-shrink-0 self-start sm:self-auto">
                    <ScoreRing score={88} size="lg" showLabel />
                  </div>
                </div>

                {/* Match Summary paragraph from AI */}
                <div className="mt-5">
                  <p className="text-[0.7rem] font-bold uppercase tracking-wider mb-1.5" style={{ color: "var(--color-muted)" }}>
                    Match Summary & Role Alignment
                  </p>
                  <div
                    className="p-3.5 rounded-lg text-xs sm:text-sm leading-relaxed"
                    style={{
                      background: "var(--color-bg)",
                      border: "1px solid var(--color-border)",
                      color: "var(--color-text)",
                    }}
                  >
                    Candidate exhibits strong technical depth in React, TypeScript, and REST API development matching 88% of core requirements. The candidate’s recent full-stack project fulfills frontend and state architecture needs. Recommendation: brush up on PostgreSQL indexing and Docker deployment before technical screening.
                  </div>
                </div>

                {/* Matched vs Missing Skills */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5">
                  {/* Matched skills */}
                  <div
                    className="p-3.5 rounded-lg"
                    style={{ background: "rgba(34, 197, 94, 0.05)", border: "1px solid rgba(34, 197, 94, 0.2)" }}
                  >
                    <p className="text-[0.6875rem] font-bold uppercase tracking-wider mb-2" style={{ color: "var(--color-green)" }}>
                      ✓ Verified Skill Matches (5)
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {["React", "TypeScript", "Node.js", "REST APIs", "Git"].map((s) => (
                        <span
                          key={s}
                          className="px-2 py-0.5 rounded text-xs font-medium"
                          style={{
                            background: "rgba(34, 197, 94, 0.12)",
                            color: "var(--color-green)",
                            border: "1px solid rgba(34, 197, 94, 0.25)",
                          }}
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Missing skills */}
                  <div
                    className="p-3.5 rounded-lg"
                    style={{ background: "rgba(234, 179, 8, 0.05)", border: "1px solid rgba(234, 179, 8, 0.2)" }}
                  >
                    <p className="text-[0.6875rem] font-bold uppercase tracking-wider mb-2" style={{ color: "var(--color-amber)" }}>
                      ! Missing Skills To Review (2)
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {["Docker", "PostgreSQL Indexing"].map((s) => (
                        <span
                          key={s}
                          className="px-2 py-0.5 rounded text-xs font-medium"
                          style={{
                            background: "rgba(234, 179, 8, 0.12)",
                            color: "var(--color-amber)",
                            border: "1px solid rgba(234, 179, 8, 0.25)",
                          }}
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Bottom Action Footer */}
              <div className="mt-6 pt-4 border-t flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
                   style={{ borderColor: "var(--color-border)" }}
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: "var(--color-muted)" }}>
                    Targeted Interview Prep:
                  </span>
                  <span className="text-xs font-semibold" style={{ color: "var(--color-gold)" }}>
                    Available on Demand
                  </span>
                </div>
                <Link href="/dashboard">
                  <Button size="sm" variant="secondary">
                    View in Your Cockpit →
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
