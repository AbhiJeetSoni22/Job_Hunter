"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ScoreRing } from "@/components/ui/Motion";

export function LandingHero() {
  return (
    <section className="relative pt-4 sm:pt-10 pb-8 sm:pb-16 overflow-hidden">
      {/* Background ambient radial glow */}
      <div
        aria-hidden="true"
        className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] sm:w-[700px] h-[350px] rounded-full pointer-events-none opacity-30"
        style={{
          background:
            "radial-gradient(circle, rgba(143, 23, 51, 0.28) 0%, rgba(201, 166, 107, 0.08) 45%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-center relative z-10">
        {/* Left Column: Hero Narrative */}
        <div className="lg:col-span-7 flex flex-col items-start">
          {/* Category Pill */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border mb-5 fade-up fade-up-1"
               style={{
                 background: "var(--color-surface)",
                 borderColor: "var(--color-accent-border)",
               }}
          >
            <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "var(--color-accent)" }} />
            <span className="text-xs font-semibold tracking-wider uppercase" style={{ color: "var(--color-gold)" }}>
              AI-Powered Job Hunting
            </span>
          </div>

          {/* Headline */}
          <h1
            className="text-3xl sm:text-5xl lg:text-5xl font-extrabold tracking-tight leading-[1.12] fade-up fade-up-2"
            style={{ color: "var(--color-text)" }}
          >
            Find Internships That Match Your{" "}
            <span
              className="relative inline-block"
              style={{
                color: "var(--color-gold)",
                textDecoration: "underline",
                textDecorationColor: "rgba(201, 166, 107, 0.35)",
                textUnderlineOffset: "6px",
              }}
            >
              Exact Skills
            </span>
          </h1>

          {/* Subtitle */}
          <p
            className="mt-5 max-w-xl text-sm sm:text-base leading-relaxed fade-up fade-up-3"
            style={{ color: "var(--color-subtle)" }}
          >
            Stop scrolling through hundreds of irrelevant listings. Upload your resume, aggregate verified openings from
            RemoteOK and YC Jobs, and let Gemini AI rank every opportunity by technical relevance, missing skills, and interview readiness.
          </p>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center gap-3.5 mt-8 w-full xs:w-auto fade-up fade-up-4">
            <Link href="/dashboard" className="w-full xs:w-auto">
              <Button size="lg" className="w-full xs:w-auto gap-2 font-semibold">
                Find My Opportunities
                <svg className="w-4 h-4 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </Button>
            </Link>
            <a href="#how-it-works" className="w-full xs:w-auto">
              <Button size="lg" variant="secondary" className="w-full xs:w-auto font-medium">
                Explore How It Works
              </Button>
            </a>
          </div>

          {/* Quick trust metrics */}
          <div className="flex items-center gap-6 mt-9 pt-6 border-t w-full max-w-lg fade-up fade-up-4"
               style={{ borderColor: "var(--color-border)" }}
          >
            <div>
              <p className="text-xl sm:text-2xl font-black" style={{ color: "var(--color-text)" }}>
                0–100%
              </p>
              <p className="text-xs uppercase tracking-wider mt-0.5" style={{ color: "var(--color-muted)" }}>
                Gemini Match Score
              </p>
            </div>
            <div className="w-px h-8" style={{ background: "var(--color-border)" }} />
            <div>
              <p className="text-xl sm:text-2xl font-black" style={{ color: "var(--color-gold)" }}>
                Multi-Board
              </p>
              <p className="text-xs uppercase tracking-wider mt-0.5" style={{ color: "var(--color-muted)" }}>
                RemoteOK + YC Jobs
              </p>
            </div>
            <div className="w-px h-8" style={{ background: "var(--color-border)" }} />
            <div>
              <p className="text-xl sm:text-2xl font-black" style={{ color: "var(--color-green)" }}>
                Zero Spam
              </p>
              <p className="text-xs uppercase tracking-wider mt-0.5" style={{ color: "var(--color-muted)" }}>
                Verified Tech Roles
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Interactive Product Preview Card */}
        <div className="lg:col-span-5 w-full fade-up fade-up-3">
          <div
            className="p-5 sm:p-6 rounded-xl relative card-elevated card-interactive border glow-accent"
            style={{
              background: "var(--color-surface)",
              borderColor: "var(--color-border)",
            }}
          >
            {/* Top header bar */}
            <div className="flex items-center justify-between pb-4 mb-4 border-b" style={{ borderColor: "var(--color-border)" }}>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: "var(--color-accent)" }} />
                <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--color-text)" }}>
                  Gemini AI Match Intelligence
                </span>
              </div>
              <Badge color="green" dot>
                Verified Active
              </Badge>
            </div>

            {/* Job Header */}
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h3 className="font-bold text-base sm:text-lg leading-snug" style={{ color: "var(--color-text)" }}>
                  Frontend Engineering Intern
                </h3>
                <p className="text-xs sm:text-sm mt-1" style={{ color: "var(--color-subtle)" }}>
                  <span className="font-semibold text-[var(--color-text)]">Nimbus Labs</span> · Remote · RemoteOK
                </p>
              </div>

              {/* Animated Circular Score Ring */}
              <ScoreRing score={94} size="md" showLabel />
            </div>

            {/* AI Fit Reasoning Box */}
            <div
              className="mt-4 p-3 rounded-lg text-xs leading-relaxed"
              style={{
                background: "var(--color-bg)",
                border: "1px solid var(--color-border)",
                color: "var(--color-subtle)",
              }}
            >
              <span className="font-semibold block mb-1" style={{ color: "var(--color-gold)" }}>
                AI Recommendation: Strong Match
              </span>
              Your React, TypeScript, and client-side performance projects directly fulfill all primary core requirements for this role.
            </div>

            {/* Matched vs Missing Skills breakdown */}
            <div className="mt-4 space-y-2">
              <div>
                <p className="text-[0.6875rem] font-semibold uppercase tracking-wider mb-1.5" style={{ color: "var(--color-muted)" }}>
                  Matched Skills (4)
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

              <div className="pt-1">
                <p className="text-[0.6875rem] font-semibold uppercase tracking-wider mb-1.5" style={{ color: "var(--color-muted)" }}>
                  Skill Gap To Study (1)
                </p>
                <div className="flex flex-wrap gap-1.5">
                  <span
                    className="px-2 py-0.5 rounded text-[0.72rem] font-medium"
                    style={{
                      background: "rgba(234, 179, 8, 0.12)",
                      color: "var(--color-amber)",
                      border: "1px solid rgba(234, 179, 8, 0.3)",
                    }}
                  >
                    ! GraphQL
                  </span>
                </div>
              </div>
            </div>

            {/* Bottom Status & CTA Action Bar */}
            <div className="mt-5 pt-4 border-t flex items-center justify-between" style={{ borderColor: "var(--color-border)" }}>
              <div className="flex items-center gap-2">
                <span className="text-xs" style={{ color: "var(--color-muted)" }}>Stage:</span>
                <span
                  className="px-2 py-0.5 rounded text-xs font-semibold"
                  style={{
                    background: "rgba(56, 189, 248, 0.12)",
                    color: "var(--color-sky)",
                    border: "1px solid rgba(56, 189, 248, 0.3)",
                  }}
                >
                  Applied
                </span>
              </div>
              <Link href="/jobs" className="text-xs font-semibold hover:underline" style={{ color: "var(--color-gold)" }}>
                View in Catalog →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
