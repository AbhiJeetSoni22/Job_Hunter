"use client";

import { ScrollReveal } from "@/components/ui/Motion";
import { StatusBadge } from "@/components/jobs/StatusBadge";
import type { JobStatus } from "@/lib/types";

interface StageItem {
  status: JobStatus;
  num: string;
  title: string;
  count: string;
  desc: string;
  actionTip: string;
}

const PIPELINE_STAGES: StageItem[] = [
  {
    status: "saved",
    num: "01",
    title: "Saved",
    count: "Bookmarked",
    desc: "Curate high-potential listings from daily scrapes. Filter by match score ≥ 80% to prioritize roles worth tailoring your outreach for.",
    actionTip: "Review missing skills to target high-yield prep.",
  },
  {
    status: "applied",
    num: "02",
    title: "Applied",
    count: "Active Submissions",
    desc: "Log submission dates, company portal links, and resume versions. Keep a clean record of exactly when and where you applied.",
    actionTip: "Automated status updates keep your pipeline synchronized.",
  },
  {
    status: "interview",
    num: "03",
    title: "Interview",
    count: "In Screening",
    desc: "Track recruiter chats, coding assessments, and system design rounds. Access role-specific prep questions tailored to the company stack.",
    actionTip: "Review Gemini-generated technical questions prior to call.",
  },
  {
    status: "offer",
    num: "04",
    title: "Offer",
    count: "Decision Stage",
    desc: "Consolidate offers with compensation, location, and deadline details. Compare team terms in a single high-contrast interface.",
    actionTip: "Evaluate team stack alignment and growth trajectory.",
  },
];

export function PipelineShowcase() {
  return (
    <section id="pipeline" className="py-14 sm:py-24 border-t relative" style={{ borderColor: "var(--color-border)" }}>
      <ScrollReveal animation="fade-up">
        <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16">
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border mb-3"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
          >
            <span className="text-xs uppercase tracking-wider font-semibold" style={{ color: "var(--color-gold)" }}>
              End-To-End Lifecycle
            </span>
          </div>
          <h2
            className="text-2xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            Manage Every Stage of the Pipeline
          </h2>
          <p
            className="mt-3 text-sm sm:text-base leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            Job Hunter doesn’t abandon you after discovery. Track your candidate lifecycle through
            a unified, high-contrast tracking board.
          </p>
        </div>
      </ScrollReveal>

      {/* Connected 4-Stage Desktop Pipeline */}
      <div className="hidden lg:block relative mb-8 max-w-6xl mx-auto">
        {/* Horizontal Connector Line */}
        <div
          aria-hidden="true"
          className="absolute top-12 left-[12%] right-[12%] h-0.5 -z-0"
          style={{
            background: "linear-gradient(90deg, rgba(201, 166, 107, 0.2) 0%, rgba(143, 23, 51, 0.4) 50%, rgba(34, 197, 94, 0.3) 100%)",
          }}
        />

        <div className="grid grid-cols-4 gap-5 relative z-10">
          {PIPELINE_STAGES.map((stage, idx) => (
            <ScrollReveal
              key={stage.status}
              animation="fade-up"
              delayMs={idx * 80}
              className="h-full"
            >
              <div
                className="p-5 rounded-2xl border h-full flex flex-col justify-between card-layer-shadow spotlight-card"
                style={{
                  background: "var(--color-surface)",
                  borderColor: "var(--color-border)",
                }}
              >
                <div>
                  {/* Top stage pill & badge */}
                  <div className="flex items-center justify-between mb-4">
                    <StatusBadge status={stage.status} />
                    <span
                      className="font-mono text-xs font-bold px-2 py-0.5 rounded border"
                      style={{
                        background: "var(--color-bg)",
                        color: "var(--color-gold)",
                        borderColor: "var(--color-border)",
                      }}
                    >
                      {stage.num}
                    </span>
                  </div>

                  <h3 className="font-bold text-base mb-1" style={{ color: "var(--color-text)" }}>
                    {stage.title}
                  </h3>
                  <p className="text-[0.7rem] font-semibold uppercase tracking-wider mb-2.5" style={{ color: "var(--color-muted)" }}>
                    {stage.count}
                  </p>

                  <p className="text-xs leading-relaxed" style={{ color: "var(--color-subtle)" }}>
                    {stage.desc}
                  </p>
                </div>

                {/* Tactical Tip */}
                <div
                  className="mt-4 pt-3 border-t text-[0.72rem] leading-normal"
                  style={{ borderColor: "var(--color-border)", color: "var(--color-subtle)" }}
                >
                  <span className="font-semibold text-[var(--color-gold)]">Tip: </span>
                  {stage.actionTip}
                </div>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>

      {/* Mobile & Tablet Vertical Connected Timeline */}
      <div className="lg:hidden flex flex-col gap-4 relative">
        {PIPELINE_STAGES.map((stage, idx) => (
          <ScrollReveal key={stage.status} animation="fade-up" delayMs={idx * 60}>
            <div
              className="p-5 rounded-xl border card-layer-shadow flex flex-col justify-between"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
              }}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <StatusBadge status={stage.status} />
                  <span
                    className="font-mono text-xs font-bold px-2 py-0.5 rounded border"
                    style={{
                      background: "var(--color-bg)",
                      color: "var(--color-gold)",
                      borderColor: "var(--color-border)",
                    }}
                  >
                    {stage.num}
                  </span>
                </div>

                <h3 className="font-bold text-base mb-1" style={{ color: "var(--color-text)" }}>
                  {stage.title}
                </h3>
                <p className="text-xs leading-relaxed" style={{ color: "var(--color-subtle)" }}>
                  {stage.desc}
                </p>
              </div>

              <div
                className="mt-3.5 pt-2.5 border-t text-[0.72rem]"
                style={{ borderColor: "var(--color-border)", color: "var(--color-subtle)" }}
              >
                <span className="font-semibold text-[var(--color-gold)]">Tip: </span>
                {stage.actionTip}
              </div>
            </div>
          </ScrollReveal>
        ))}
      </div>

      {/* Terminal Archive State Note */}
      <div className="mt-8 text-center">
        <ScrollReveal animation="fade-up" delayMs={250}>
          <div
            className="p-3.5 rounded-xl border inline-flex items-center gap-3 text-xs mx-auto max-w-xl"
            style={{ background: "var(--color-bg)", borderColor: "var(--color-border)" }}
          >
            <span style={{ color: "var(--color-muted)" }}>At any point:</span>
            <StatusBadge status="rejected" />
            <span style={{ color: "var(--color-subtle)" }}>
              Archive non-responsive or closed roles with one click to keep your active board uncluttered.
            </span>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
