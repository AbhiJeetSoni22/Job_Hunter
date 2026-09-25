"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { ScrollReveal } from "@/components/ui/Motion";

export function FinalCta() {
  return (
    <section className="py-16 sm:py-24 border-t" style={{ borderColor: "var(--color-border)" }}>
      <ScrollReveal animation="fade-up">
        <div
          className="rounded-2xl border p-8 sm:p-14 text-center max-w-3xl mx-auto card-elevated relative overflow-hidden"
          style={{
            background: "linear-gradient(180deg, var(--color-surface) 0%, rgba(143, 23, 51, 0.12) 100%)",
            borderColor: "var(--color-accent-border)",
          }}
        >
          {/* Subtle accent badge */}
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border mb-4 text-xs font-semibold uppercase tracking-wider"
            style={{
              background: "var(--color-bg)",
              borderColor: "var(--color-accent-border)",
              color: "var(--color-gold)",
            }}
          >
            <span>Ready for your next opportunity?</span>
          </div>

          <h2
            className="text-2xl sm:text-4xl font-extrabold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            Stop searching blindly.
          </h2>

          <p
            className="mt-3 text-sm sm:text-base max-w-lg mx-auto leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            Let AI match your actual engineering skills to verified internships and track your progress in one unified cockpit.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3.5 mt-8">
            <Link href="/dashboard" className="w-full xs:w-auto">
              <Button size="lg" className="w-full xs:w-auto font-semibold px-8">
                Start Hunting
              </Button>
            </Link>
            <Link href="/login" className="w-full xs:w-auto">
              <Button size="lg" variant="secondary" className="w-full xs:w-auto">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </ScrollReveal>
    </section>
  );
}
