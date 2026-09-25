"use client";

import { ScrollReveal } from "@/components/ui/Motion";
import { StatusBadge } from "@/components/jobs/StatusBadge";
import type { JobStatus } from "@/lib/types";

const PIPELINE_STAGES: {
  status: JobStatus;
  title: string;
  desc: string;
  tip: string;
}[] = [
  {
    status: "saved",
    title: "1. Saved",
    desc: "Bookmark promising listings from your daily matches to tailor your application or review later.",
    tip: "Filter by match score ≥ 80% to prioritize high-value roles.",
  },
  {
    status: "applied",
    title: "2. Applied",
    desc: "Mark the job as applied once you submit your application through the official company link.",
    tip: "Track submission dates so you know when to follow up.",
  },
  {
    status: "interview",
    title: "3. Interview",
    desc: "Recruiter screen, technical challenge, or team interview scheduled with hiring teams.",
    tip: "Generate targeted technical & behavioral interview questions.",
  },
  {
    status: "offer",
    title: "4. Offer",
    desc: "Official internship or job offer received with compensation, deadline, and start date details.",
    tip: "Compare multiple offers in your unified dashboard.",
  },
];

export function PipelineShowcase() {
  return (
    <section className="py-12 sm:py-20 border-t" style={{ borderColor: "var(--color-border)" }}>
      <ScrollReveal animation="fade-up">
        <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16">
          <p
            className="text-xs uppercase tracking-wider font-semibold mb-2"
            style={{ color: "var(--color-gold)" }}
          >
            End-To-End Workflow
          </p>
          <h2
            className="text-2xl sm:text-4xl font-extrabold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            Manage Every Stage of the Pipeline
          </h2>
          <p
            className="mt-3 text-sm sm:text-base leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            Job Hunter doesn’t abandon you after search. Track your candidate lifecycle in one single, high-contrast board.
          </p>
        </div>
      </ScrollReveal>

      {/* Pipeline 4-Stage Horizontal Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5 mb-8">
        {PIPELINE_STAGES.map((stage, idx) => (
          <ScrollReveal
            key={stage.status}
            animation="fade-up"
            delayMs={idx * 75}
            className="h-full"
          >
            <div
              className="p-5 rounded-xl border h-full flex flex-col justify-between card-interactive"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
              }}
            >
              <div>
                <div className="flex items-center justify-between mb-3.5">
                  <StatusBadge status={stage.status} />
                  <span className="font-mono text-xs font-bold" style={{ color: "var(--color-muted)" }}>
                    0{idx + 1}
                  </span>
                </div>

                <h3
                  className="font-bold text-base mb-2"
                  style={{ color: "var(--color-text)" }}
                >
                  {stage.title}
                </h3>

                <p
                  className="text-xs leading-relaxed"
                  style={{ color: "var(--color-subtle)" }}
                >
                  {stage.desc}
                </p>
              </div>

              {/* Action Tip */}
              <div
                className="mt-4 pt-3 border-t text-[0.72rem] leading-normal"
                style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
              >
                <span className="font-semibold" style={{ color: "var(--color-gold)" }}>Tip: </span>
                {stage.tip}
              </div>
            </div>
          </ScrollReveal>
        ))}
      </div>

      {/* Terminal or Alternate State Note */}
      <ScrollReveal animation="fade-up" delayMs={300}>
        <div
          className="p-3.5 rounded-lg border text-center max-w-xl mx-auto flex items-center justify-center gap-3 text-xs"
          style={{ background: "var(--color-bg)", borderColor: "var(--color-border)" }}
        >
          <span style={{ color: "var(--color-muted)" }}>At any point:</span>
          <StatusBadge status="rejected" />
          <span style={{ color: "var(--color-subtle)" }}>
            Archive rejected applications to keep your active pipeline clean.
          </span>
        </div>
      </ScrollReveal>
    </section>
  );
}
