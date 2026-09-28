"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { ScrollReveal } from "@/components/ui/Motion";

export function FinalCta() {
  return (
    <section className="py-16 sm:py-28 border-t relative overflow-hidden" style={{ borderColor: "var(--color-border)" }}>
      {/* Background ambient radial glow */}
      <div
        aria-hidden="true"
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] rounded-full pointer-events-none opacity-30 -z-10"
        style={{
          background:
            "radial-gradient(circle, rgba(143, 23, 51, 0.4) 0%, rgba(201, 166, 107, 0.12) 50%, transparent 75%)",
          filter: "blur(80px)",
        }}
      />

      <ScrollReveal animation="scale-in">
        <div
          className="rounded-3xl border p-8 sm:p-16 text-center max-w-4xl mx-auto card-layer-shadow relative overflow-hidden"
          style={{
            background: "linear-gradient(180deg, var(--color-surface) 0%, rgba(143, 23, 51, 0.12) 100%)",
            borderColor: "var(--color-accent-border)",
          }}
        >
          {/* Subtle accent badge */}
          <div
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border mb-5 text-xs font-semibold uppercase tracking-wider"
            style={{
              background: "var(--color-bg)",
              borderColor: "var(--color-accent-border)",
              color: "var(--color-gold)",
            }}
          >
            <span>Ready to accelerate your job hunt?</span>
          </div>

          <h2
            className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.1]"
            style={{ color: "var(--color-text)" }}
          >
            Stop Searching Blindly.
          </h2>

          <p
            className="mt-5 text-sm sm:text-base max-w-xl mx-auto leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            Match your real codebase skills against verified technical roles across RemoteOK and Y Combinator.
            Identify preparation gaps, rank your opportunities, and track every application in one unified command center.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 mt-9">
            <Link href="/jobs" className="w-full xs:w-auto">
              <Button size="lg" className="w-full xs:w-auto font-semibold px-8 btn-fx gap-2">
                <span>Find My Opportunities</span>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </Button>
            </Link>
            <Link href="/resume" className="w-full xs:w-auto">
              <Button size="lg" variant="secondary" className="w-full xs:w-auto font-medium px-7 btn-fx">
                Upload Resume First
              </Button>
            </Link>
          </div>
        </div>
      </ScrollReveal>
    </section>
  );
}
