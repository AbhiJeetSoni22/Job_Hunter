"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ScoreRing } from "@/components/ui/Motion";

export function LandingHero() {
  const [activeTab, setActiveTab] = useState<"fit" | "skills" | "gaps">("fit");

  return (
    <section className="relative pt-6 sm:pt-14 pb-12 sm:pb-20 overflow-hidden">
      {/* 0ms: Ambient background glow */}
      <div
        aria-hidden="true"
        className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] sm:w-[850px] h-[400px] rounded-full pointer-events-none opacity-40 transition-opacity duration-1000"
        style={{
          background:
            "radial-gradient(circle, rgba(143, 23, 51, 0.25) 0%, rgba(201, 166, 107, 0.08) 45%, transparent 75%)",
          filter: "blur(70px)",
        }}
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center relative z-10">
        {/* Left Column: Editorial Headline & Actions */}
        <div className="lg:col-span-6 xl:col-span-7 flex flex-col items-start">
          {/* 100ms: Eyebrow Badge */}
          <div
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border mb-6 fade-up fade-up-1"
            style={{
              background: "var(--color-surface)",
              borderColor: "var(--color-accent-border)",
            }}
          >
            <span
              className="w-2 h-2 rounded-full animate-pulse"
              style={{ background: "var(--color-accent)" }}
            />
            <span
              className="text-[0.6875rem] sm:text-xs font-semibold tracking-wider uppercase"
              style={{ color: "var(--color-gold)" }}
            >
              AI-Powered Technical Job Discovery
            </span>
          </div>

          {/* 200ms: Editorial Headline */}
          <h1
            className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.08] fade-up fade-up-2"
            style={{ color: "var(--color-text)" }}
          >
            See Which Jobs{" "}
            <span
              className="relative inline-block"
              style={{
                color: "var(--color-gold)",
                textDecoration: "underline",
                textDecorationColor: "rgba(201, 166, 107, 0.35)",
                textUnderlineOffset: "8px",
              }}
            >
              Actually Match
            </span>{" "}
            Your Skills.
          </h1>

          {/* 300ms: Concrete Supporting Description */}
          <p
            className="mt-6 max-w-xl text-sm sm:text-base leading-relaxed fade-up fade-up-3"
            style={{ color: "var(--color-subtle)" }}
          >
            Stop scrolling through hundreds of unsorted listings. Upload your resume, aggregate verified
            software engineering openings across RemoteOK and YC Jobs, and let Gemini AI evaluate
            your technical fit, missing concepts, and interview readiness.
          </p>

          {/* 400ms: Magnetic CTAs */}
          <div className="flex flex-wrap items-center gap-3.5 mt-8 w-full xs:w-auto fade-up fade-up-4">
            <Link href="/jobs" className="w-full xs:w-auto">
              <Button size="lg" className="w-full xs:w-auto gap-2 font-semibold btn-fx">
                <span>Explore Scored Roles</span>
                <svg
                  className="w-4 h-4 transition-transform group-hover:translate-x-1"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </Button>
            </Link>
            <Link href="/resume" className="w-full xs:w-auto">
              <Button size="lg" variant="secondary" className="w-full xs:w-auto font-medium btn-fx gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span>Upload Resume</span>
              </Button>
            </Link>
          </div>

          {/* 500ms: Concrete Trust Metrics */}
          <div
            className="grid grid-cols-3 gap-4 sm:gap-6 mt-10 pt-6 border-t w-full max-w-lg fade-up fade-up-4"
            style={{ borderColor: "var(--color-border)" }}
          >
            <div>
              <p className="text-xl sm:text-2xl font-black" style={{ color: "var(--color-text)" }}>
                0–100%
              </p>
              <p className="text-[0.6875rem] uppercase tracking-wider mt-0.5" style={{ color: "var(--color-muted)" }}>
                Semantic Match
              </p>
            </div>
            <div className="border-l pl-4 sm:pl-6" style={{ borderColor: "var(--color-border)" }}>
              <p className="text-xl sm:text-2xl font-black" style={{ color: "var(--color-gold)" }}>
                Multi-Board
              </p>
              <p className="text-[0.6875rem] uppercase tracking-wider mt-0.5" style={{ color: "var(--color-muted)" }}>
                RemoteOK + YC Jobs
              </p>
            </div>
            <div className="border-l pl-4 sm:pl-6" style={{ borderColor: "var(--color-border)" }}>
              <p className="text-xl sm:text-2xl font-black" style={{ color: "var(--color-green)" }}>
                Verified
              </p>
              <p className="text-[0.6875rem] uppercase tracking-wider mt-0.5" style={{ color: "var(--color-muted)" }}>
                Zero Spam Roles
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Layered Interactive Product Preview */}
        <div className="lg:col-span-6 xl:col-span-5 w-full relative fade-up fade-up-3">
          {/* Subtle background offset card for visual depth */}
          <div
            aria-hidden="true"
            className="absolute inset-0 translate-x-3 translate-y-3 rounded-2xl border pointer-events-none opacity-40 sm:opacity-50"
            style={{
              background: "var(--color-surface)",
              borderColor: "var(--color-border)",
            }}
          />

          {/* 500ms: Main Product Window */}
          <div
            className="relative rounded-2xl border card-layer-shadow spotlight-card"
            style={{
              background: "var(--color-surface)",
              borderColor: "var(--color-border)",
            }}
          >
            {/* Window Chrome Header Bar */}
            <div
              className="flex items-center justify-between px-4 sm:px-5 py-3 border-b"
              style={{
                background: "var(--color-bg-subtle)",
                borderColor: "var(--color-border)",
              }}
            >
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500/40 inline-block" />
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/40 inline-block" />
                <span className="w-2.5 h-2.5 rounded-full bg-green-500/40 inline-block" />
                <span className="text-[0.7rem] font-mono ml-2 hidden sm:inline-block" style={{ color: "var(--color-muted)" }}>
                  match-evaluator // gemini-2.5-flash
                </span>
              </div>
              <span
                className="text-[0.625rem] font-semibold uppercase tracking-wider px-2 py-0.5 rounded border"
                style={{
                  background: "var(--color-bg)",
                  borderColor: "var(--color-border)",
                  color: "var(--color-gold)",
                }}
              >
                Illustrative Preview
              </span>
            </div>

            {/* Inner Content Area */}
            <div className="p-5 sm:p-6 space-y-4">
              {/* Job Title & Score Row */}
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <Badge color="green" dot>
                      Verified Active
                    </Badge>
                    <span className="text-xs" style={{ color: "var(--color-muted)" }}>·</span>
                    <span className="text-xs" style={{ color: "var(--color-muted)" }}>RemoteOK</span>
                  </div>
                  <h3 className="font-bold text-base sm:text-lg leading-snug" style={{ color: "var(--color-text)" }}>
                    Frontend Engineering Intern
                  </h3>
                  <p className="text-xs sm:text-sm mt-0.5" style={{ color: "var(--color-subtle)" }}>
                    <span className="font-semibold text-[var(--color-text)]">Sample: Nimbus Labs</span> · Remote
                  </p>
                </div>

                {/* 600ms: Floating Match Score Ring */}
                <div
                  className="p-2.5 rounded-xl border flex flex-col items-center flex-shrink-0"
                  style={{
                    background: "var(--color-bg)",
                    borderColor: "rgba(34, 197, 94, 0.3)",
                    boxShadow: "0 8px 24px -4px rgba(34, 197, 94, 0.15)",
                  }}
                >
                  <ScoreRing score={94} size="md" showLabel />
                </div>
              </div>

              {/* Interactive View Toggles */}
              <div
                className="flex items-center p-1 rounded-lg border text-xs"
                style={{
                  background: "var(--color-bg)",
                  borderColor: "var(--color-border)",
                }}
              >
                {[
                  { id: "fit", label: "Fit Reasoning" },
                  { id: "skills", label: "Matched Skills (4)" },
                  { id: "gaps", label: "Skill Gaps (1)" },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id as typeof activeTab)}
                    className="flex-1 py-1.5 px-2 rounded-md font-medium text-center transition-all cursor-pointer"
                    style={{
                      background: activeTab === tab.id ? "var(--color-surface)" : "transparent",
                      color: activeTab === tab.id ? "var(--color-text)" : "var(--color-muted)",
                      border: activeTab === tab.id ? "1px solid var(--color-border)" : "1px solid transparent",
                    }}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab Dynamic Content */}
              <div
                className="p-3.5 rounded-xl min-h-[95px] flex items-center text-xs leading-relaxed"
                style={{
                  background: "var(--color-bg-subtle)",
                  border: "1px solid var(--color-border)",
                }}
              >
                {activeTab === "fit" && (
                  <div>
                    <span className="font-semibold block mb-1" style={{ color: "var(--color-gold)" }}>
                      AI Match Assessment: High Alignment (94%)
                    </span>
                    <p style={{ color: "var(--color-subtle)" }}>
                      Your production React, TypeScript, and client performance work strongly match the core
                      requirements. Demonstrated Next.js routing fulfills team stack needs directly.
                    </p>
                  </div>
                )}

                {activeTab === "skills" && (
                  <div className="w-full">
                    <p className="text-[0.6875rem] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-green)" }}>
                      ✓ Verified Skill Alignment
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {["React", "TypeScript", "Next.js", "TailwindCSS"].map((s) => (
                        <span
                          key={s}
                          className="px-2 py-0.5 rounded text-[0.72rem] font-medium"
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

                {activeTab === "gaps" && (
                  <div className="w-full">
                    <p className="text-[0.6875rem] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-amber)" }}>
                      ! Concept to Review Before Interview
                    </p>
                    <div className="flex flex-wrap gap-1.5 items-center">
                      <span
                        className="px-2 py-0.5 rounded text-[0.72rem] font-medium"
                        style={{
                          background: "rgba(234, 179, 8, 0.12)",
                          color: "var(--color-amber)",
                          border: "1px solid rgba(234, 179, 8, 0.3)",
                        }}
                      >
                        ! GraphQL Query Optimization
                      </span>
                      <span className="text-[0.7rem] ml-1" style={{ color: "var(--color-muted)" }}>
                        (Listed in secondary nice-to-haves)
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Bottom Action Row */}
              <div
                className="pt-3 border-t flex items-center justify-between text-xs"
                style={{ borderColor: "var(--color-border)" }}
              >
                <div className="flex items-center gap-2">
                  <span className="text-[0.7rem]" style={{ color: "var(--color-muted)" }}>
                    Pipeline Stage:
                  </span>
                  <span
                    className="px-2 py-0.5 rounded font-semibold text-[0.7rem]"
                    style={{
                      background: "rgba(56, 189, 248, 0.12)",
                      color: "var(--color-sky)",
                      border: "1px solid rgba(56, 189, 248, 0.3)",
                    }}
                  >
                    Applied
                  </span>
                </div>
                <Link
                  href="/jobs"
                  className="font-semibold transition-colors hover:underline text-[0.75rem]"
                  style={{ color: "var(--color-gold)" }}
                >
                  View Scored Catalog →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
