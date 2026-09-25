"use client";

import { ScrollReveal } from "@/components/ui/Motion";

const FRICTION_POINTS = [
  {
    step: "01",
    title: "Scattered Job Boards",
    desc: "Hopping between RemoteOK, Y Combinator, and dozens of disparate sites creates duplicate postings, expired listings, and search fatigue.",
    icon: "🌐",
    accent: "var(--color-amber)",
  },
  {
    step: "02",
    title: "Keyword Guesswork",
    desc: "Generic search bars match superficial keywords, completely ignoring your real framework depth, projects, and codebase experience.",
    icon: "🔍",
    accent: "var(--color-sky)",
  },
  {
    step: "03",
    title: "Blind Applications",
    desc: "Submitting applications without knowing your true fit score or which specific technologies you are missing leads to wasted effort.",
    icon: "🎯",
    accent: "var(--color-red)",
  },
  {
    step: "04",
    title: "Disorganized Pipeline",
    desc: "Tracking dozens of application links, response deadlines, and interview notes across ad-hoc spreadsheets causes missed opportunities.",
    icon: "📊",
    accent: "var(--color-accent)",
  },
];

export function ProductProblem() {
  return (
    <section className="py-10 sm:py-16 border-t" style={{ borderColor: "var(--color-border)" }}>
      <ScrollReveal animation="fade-up">
        <div className="text-center max-w-2xl mx-auto mb-10 sm:mb-14">
          <p
            className="text-xs uppercase tracking-wider font-semibold mb-2"
            style={{ color: "var(--color-gold)" }}
          >
            The Problem
          </p>
          <h2
            className="text-2xl sm:text-4xl font-extrabold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            The Traditional Search Process Is Broken
          </h2>
          <p
            className="mt-3 text-sm sm:text-base leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            Most developers spend hours manually hunting through unsorted job boards instead of focusing on interview preparation.
          </p>
        </div>
      </ScrollReveal>

      {/* 4-Column Friction Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5 mb-8 sm:mb-12">
        {FRICTION_POINTS.map((item, idx) => (
          <ScrollReveal
            key={item.title}
            animation="fade-up"
            delayMs={idx * 75}
            className="h-full"
          >
            <div
              className="p-5 sm:p-6 rounded-xl border h-full flex flex-col justify-between card-interactive"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
              }}
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-2xl">{item.icon}</span>
                  <span
                    className="font-mono text-xs font-bold px-2 py-0.5 rounded"
                    style={{
                      background: "var(--color-bg)",
                      color: item.accent,
                      border: "1px solid var(--color-border)",
                    }}
                  >
                    {item.step}
                  </span>
                </div>
                <h3
                  className="font-bold text-base sm:text-lg mb-2"
                  style={{ color: "var(--color-text)" }}
                >
                  {item.title}
                </h3>
                <p
                  className="text-xs sm:text-sm leading-relaxed"
                  style={{ color: "var(--color-subtle)" }}
                >
                  {item.desc}
                </p>
              </div>
            </div>
          </ScrollReveal>
        ))}
      </div>

      {/* Resolution transition card */}
      <ScrollReveal animation="fade-up" delayMs={300}>
        <div
          className="p-5 sm:p-7 rounded-xl border text-center max-w-3xl mx-auto card-elevated"
          style={{
            background: "linear-gradient(180deg, var(--color-surface) 0%, rgba(143, 23, 51, 0.08) 100%)",
            borderColor: "var(--color-accent-border)",
          }}
        >
          <div className="inline-flex items-center justify-center w-8 h-8 rounded-full mb-3"
               style={{ background: "rgba(143, 23, 51, 0.2)", color: "var(--color-gold)" }}>
            ⚡
          </div>
          <h3
            className="text-lg sm:text-xl font-bold"
            style={{ color: "var(--color-text)" }}
          >
            Job Hunter brings the entire process together.
          </h3>
          <p
            className="mt-2 text-xs sm:text-sm max-w-xl mx-auto leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            Automated scraping discovers new openings, Gemini AI maps them against your exact resume skills,
            and your personal pipeline manages every application from discovery to offer.
          </p>
        </div>
      </ScrollReveal>
    </section>
  );
}
