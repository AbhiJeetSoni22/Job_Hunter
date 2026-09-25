"use client";

import { ScrollReveal } from "@/components/ui/Motion";

const WORKFLOW_STEPS = [
  {
    num: "01",
    label: "Discover",
    title: "Multi-Source Aggregation",
    desc: "Scrapers pull verified software engineering and internship openings directly from RemoteOK and Y Combinator boards.",
    icon: "🌐",
  },
  {
    num: "02",
    label: "Upload Resume",
    title: "Gemini Skill Extraction",
    desc: "Upload your PDF. Gemini AI parses your projects, frameworks, libraries, and languages with zero manual data entry.",
    icon: "📄",
  },
  {
    num: "03",
    label: "AI Match",
    title: "Relevance Scoring (0–100%)",
    desc: "Each job description is analyzed against your skills, computing an exact match percentage, strengths, and missing skills.",
    icon: "🎯",
  },
  {
    num: "04",
    label: "Apply",
    title: "Targeted Application & Prep",
    desc: "Review your alignment, study missing concepts, generate interview prep questions, and apply directly on the employer site.",
    icon: "⚡",
  },
  {
    num: "05",
    label: "Track",
    title: "Unified Pipeline",
    desc: "Move roles from Saved to Applied, Interview, and Offer with a single click, keeping your job search organized.",
    icon: "📊",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-12 sm:py-20 border-t" style={{ borderColor: "var(--color-border)" }}>
      <ScrollReveal animation="fade-up">
        <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16">
          <p
            className="text-xs uppercase tracking-wider font-semibold mb-2"
            style={{ color: "var(--color-gold)" }}
          >
            Product Workflow
          </p>
          <h2
            className="text-2xl sm:text-4xl font-extrabold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            How Job Hunter Works
          </h2>
          <p
            className="mt-3 text-sm sm:text-base leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            From raw resume to scored interview pipeline in five clear, automated steps.
          </p>
        </div>
      </ScrollReveal>

      {/* Workflow Steps */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 lg:gap-3 relative">
        {WORKFLOW_STEPS.map((step, idx) => (
          <ScrollReveal
            key={step.num}
            animation="fade-up"
            delayMs={idx * 90}
            className="h-full relative"
          >
            <div
              className="p-5 rounded-xl border h-full flex flex-col justify-between card-interactive relative"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
              }}
            >
              {/* Step indicator header */}
              <div>
                <div className="flex items-center justify-between mb-3.5">
                  <span className="text-2xl">{step.icon}</span>
                  <span
                    className="font-mono text-xs font-bold px-2 py-0.5 rounded"
                    style={{
                      background: "var(--color-bg)",
                      color: "var(--color-gold)",
                      border: "1px solid var(--color-border)",
                    }}
                  >
                    {step.num}
                  </span>
                </div>

                <p
                  className="text-[0.7rem] font-bold uppercase tracking-wider mb-1"
                  style={{ color: "var(--color-muted)" }}
                >
                  {step.label}
                </p>

                <h3
                  className="font-bold text-sm sm:text-base mb-2"
                  style={{ color: "var(--color-text)" }}
                >
                  {step.title}
                </h3>

                <p
                  className="text-xs leading-relaxed"
                  style={{ color: "var(--color-subtle)" }}
                >
                  {step.desc}
                </p>
              </div>

              {/* Progress step indicator bar */}
              <div className="mt-4 pt-3 border-t flex items-center justify-between" style={{ borderColor: "var(--color-border)" }}>
                <span className="text-[0.6875rem] font-medium" style={{ color: "var(--color-muted)" }}>
                  Step {idx + 1} of 5
                </span>
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{
                    background: idx === 0 ? "var(--color-gold)" : idx === 2 ? "var(--color-green)" : "var(--color-accent)",
                  }}
                />
              </div>
            </div>
          </ScrollReveal>
        ))}
      </div>
    </section>
  );
}
