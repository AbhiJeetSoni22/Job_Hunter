"use client";

import { useState } from "react";
import { ScrollReveal } from "@/components/ui/Motion";

const FRICTION_POINTS = [
  {
    step: "01",
    title: "Scattered Job Boards",
    short: "Multi-tab fatigue",
    desc: "Hopping between RemoteOK, Y Combinator, and dozens of disparate sites causes duplicated applications, expired listings, and immense search fatigue.",
    icon: "🌐",
    accent: "var(--color-amber)",
  },
  {
    step: "02",
    title: "Keyword Guesswork",
    short: "Superficial ATS matching",
    desc: "Traditional search engines match blunt keywords like 'React', ignoring your actual project depth, architecture knowledge, and practical codebase experience.",
    icon: "🔍",
    accent: "var(--color-sky)",
  },
  {
    step: "03",
    title: "Blind Applications",
    short: "Uncertain skill alignment",
    desc: "Submitting applications without knowing your true fit score or which specific technologies you are missing leads to low response rates and wasted time.",
    icon: "🎯",
    accent: "var(--color-red)",
  },
  {
    step: "04",
    title: "Disorganized Pipeline",
    short: "Messy spreadsheets",
    desc: "Tracking interview stages, recruiter follow-ups, and application notes in disjointed spreadsheets makes critical opportunities slip through the cracks.",
    icon: "📊",
    accent: "var(--color-accent)",
  },
];

export function ProductProblem() {
  const [activeFriction, setActiveFriction] = useState<number>(0);

  return (
    <section id="problem" className="py-14 sm:py-24 border-t relative" style={{ borderColor: "var(--color-border)" }}>
      {/* Background ambient accent */}
      <div
        aria-hidden="true"
        className="absolute top-1/2 right-0 w-[400px] h-[350px] rounded-full pointer-events-none opacity-20 -z-10"
        style={{
          background: "radial-gradient(circle, rgba(143, 23, 51, 0.3) 0%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-start">
        {/* Left Column: Big Editorial Statement */}
        <div className="lg:col-span-5 sticky top-24">
          <ScrollReveal animation="fade-up">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border mb-4"
                 style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
              <span className="text-xs uppercase tracking-wider font-semibold" style={{ color: "var(--color-gold)" }}>
                The Problem
              </span>
            </div>

            <h2
              className="text-2xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight leading-[1.12]"
              style={{ color: "var(--color-text)" }}
            >
              The Traditional Job Hunt Is Broken.
            </h2>

            <p
              className="mt-5 text-sm sm:text-base leading-relaxed"
              style={{ color: "var(--color-subtle)" }}
            >
              Developers spend countless hours sifting through noisy job boards with keyword-matching
              filters that don’t understand actual codebase experience.
            </p>

            <div
              className="mt-8 p-4 rounded-xl border"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
              }}
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">⚠️</span>
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--color-gold)" }}>
                    Friction Breakdown
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--color-subtle)" }}>
                    Select any friction point on the right to inspect how it derails your search.
                  </p>
                </div>
              </div>
            </div>
          </ScrollReveal>
        </div>

        {/* Right Column: Editorial Asymmetric Problem Progression */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          {FRICTION_POINTS.map((item, idx) => {
            const isSelected = activeFriction === idx;
            return (
              <ScrollReveal
                key={item.title}
                animation="fade-up"
                delayMs={idx * 80}
              >
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => setActiveFriction(idx)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setActiveFriction(idx);
                    }
                  }}
                  className="p-5 sm:p-6 rounded-xl border text-left transition-all duration-200 cursor-pointer group"
                  style={{
                    background: isSelected ? "var(--color-surface-hover)" : "var(--color-surface)",
                    borderColor: isSelected ? item.accent : "var(--color-border)",
                    boxShadow: isSelected
                      ? `0 10px 30px -8px rgba(0, 0, 0, 0.7), 0 0 16px -4px ${item.accent}33`
                      : "none",
                  }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4">
                      <div
                        className="w-10 h-10 rounded-lg flex items-center justify-center text-xl flex-shrink-0 border"
                        style={{
                          background: "var(--color-bg)",
                          borderColor: isSelected ? item.accent : "var(--color-border)",
                        }}
                      >
                        {item.icon}
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span
                            className="font-mono text-xs font-bold px-2 py-0.5 rounded border"
                            style={{
                              background: "var(--color-bg)",
                              color: item.accent,
                              borderColor: "var(--color-border)",
                            }}
                          >
                            {item.step}
                          </span>
                          <span className="text-xs" style={{ color: "var(--color-muted)" }}>
                            {item.short}
                          </span>
                        </div>
                        <h3
                          className="font-bold text-base sm:text-lg transition-colors group-hover:text-[var(--color-text)]"
                          style={{ color: isSelected ? "var(--color-text)" : "var(--color-subtle)" }}
                        >
                          {item.title}
                        </h3>
                        <p
                          className="text-xs sm:text-sm mt-2 leading-relaxed"
                          style={{ color: "var(--color-subtle)" }}
                        >
                          {item.desc}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </ScrollReveal>
            );
          })}
        </div>
      </div>

      {/* Visual Narrative Transition Bridge */}
      <div className="mt-12 sm:mt-16">
        <ScrollReveal animation="scale-in">
          <div
            className="p-6 sm:p-8 rounded-2xl border text-center max-w-4xl mx-auto card-layer-shadow relative overflow-hidden"
            style={{
              background: "linear-gradient(180deg, var(--color-surface) 0%, rgba(143, 23, 51, 0.1) 100%)",
              borderColor: "var(--color-accent-border)",
            }}
          >
            <div className="inline-flex items-center justify-center w-9 h-9 rounded-full mb-3"
                 style={{ background: "rgba(143, 23, 51, 0.25)", color: "var(--color-gold)" }}>
              ⚡
            </div>
            <h3
              className="text-xl sm:text-2xl font-bold tracking-tight"
              style={{ color: "var(--color-text)" }}
            >
              Job Hunter brings the entire process together.
            </h3>
            <p
              className="mt-2 text-xs sm:text-sm max-w-xl mx-auto leading-relaxed"
              style={{ color: "var(--color-subtle)" }}
            >
              Automated multi-source scraping aggregates new roles, Gemini AI maps them against your actual
              resume skills, and your personal pipeline organizes every step from discovery to signed offer.
            </p>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
