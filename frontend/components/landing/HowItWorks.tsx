"use client";

import { useState } from "react";
import { ScrollReveal, ScoreRing } from "@/components/ui/Motion";
import { Badge } from "@/components/ui/Badge";
import Link from "next/link";
import { Button } from "@/components/ui/Button";

const WORKFLOW_STEPS = [
  {
    num: "01",
    label: "Discover",
    title: "Multi-Source Aggregation",
    desc: "Background scrapers monitor verified engineering listings across RemoteOK and Y Combinator Work at a Startup, de-duplicating and standardizing every opening.",
    icon: "🌐",
    previewTitle: "Automated Listing Aggregator",
    previewDetail: "Scrapes technical roles in real-time, removing dead links and expired requisitions.",
    badge: "RemoteOK + YC Jobs",
  },
  {
    num: "02",
    label: "Upload Resume",
    title: "Gemini Skill Extraction",
    desc: "Upload your resume in PDF format. Gemini AI automatically parses your programming languages, frameworks, developer tooling, and practical project stack.",
    icon: "📄",
    previewTitle: "Zero Manual Data Entry",
    previewDetail: "Instantly extracts 10–25 verified technical competencies directly into your profile.",
    badge: "Gemini 2.5 Flash",
  },
  {
    num: "03",
    label: "AI Match",
    title: "Relevance Scoring (0–100%)",
    desc: "Every target job description is semantically evaluated against your verified skills. The engine computes your match percentage and highlights missing skills.",
    icon: "🎯",
    previewTitle: "Semantic Fit Engine",
    previewDetail: "Ranks opportunities by alignment with actionable gap analysis before you apply.",
    badge: "0–100% Score Ring",
  },
  {
    num: "04",
    label: "Apply & Prep",
    title: "Targeted Interview Preparation",
    desc: "Study specific technology gaps identified by the AI and generate role-tailored technical questions so you enter screens confident and prepared.",
    icon: "⚡",
    previewTitle: "AI Interview Readiness",
    previewDetail: "Generate technical screening questions based specifically on the target company stack.",
    badge: "Role-Specific Prep",
  },
  {
    num: "05",
    label: "Track",
    title: "Unified Application Pipeline",
    desc: "Seamlessly transition opportunities across Saved, Applied, Interview, and Offer stages. Maintain status, timestamps, and application notes in one board.",
    icon: "📊",
    previewTitle: "Complete Lifecycle Tracking",
    previewDetail: "No more disconnected spreadsheets or lost application links.",
    badge: "Single Command Center",
  },
];

export function HowItWorks() {
  const [activeStep, setActiveStep] = useState(0);
  const current = WORKFLOW_STEPS[activeStep];

  return (
    <section id="how-it-works" className="py-14 sm:py-24 border-t relative" style={{ borderColor: "var(--color-border)" }}>
      <ScrollReveal animation="fade-up">
        <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16">
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border mb-3"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
          >
            <span className="text-xs uppercase tracking-wider font-semibold" style={{ color: "var(--color-gold)" }}>
              Product Workflow
            </span>
          </div>
          <h2
            className="text-2xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight"
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

      {/* Desktop Interactive Stepper (Hidden on mobile) */}
      <div className="hidden md:block">
        {/* Step Tabs Row with Connecting Line */}
        <div className="relative mb-8 max-w-5xl mx-auto">
          {/* Progress background line */}
          <div
            className="absolute top-1/2 left-0 right-0 h-0.5 -translate-y-1/2 -z-0"
            style={{ background: "var(--color-border)" }}
          />
          {/* Active progress line */}
          <div
            className="absolute top-1/2 left-0 h-0.5 -translate-y-1/2 -z-0 transition-all duration-300"
            style={{
              width: `${(activeStep / (WORKFLOW_STEPS.length - 1)) * 100}%`,
              background: "linear-gradient(90deg, var(--color-accent) 0%, var(--color-gold) 100%)",
            }}
          />

          <div className="grid grid-cols-5 gap-3 relative z-10">
            {WORKFLOW_STEPS.map((step, idx) => {
              const isActive = activeStep === idx;
              const isPassed = activeStep > idx;
              return (
                <button
                  key={step.num}
                  type="button"
                  onClick={() => setActiveStep(idx)}
                  className="flex flex-col items-center group cursor-pointer text-center p-2 rounded-xl transition-all"
                >
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold border transition-all duration-200"
                    style={{
                      background: isActive
                        ? "var(--color-accent)"
                        : isPassed
                          ? "var(--color-surface-hover)"
                          : "var(--color-surface)",
                      borderColor: isActive
                        ? "var(--color-gold)"
                        : isPassed
                          ? "var(--color-accent-border)"
                          : "var(--color-border)",
                      color: isActive ? "#F5F1E8" : isPassed ? "var(--color-gold)" : "var(--color-muted)",
                      boxShadow: isActive ? "0 0 16px rgba(143, 23, 51, 0.4)" : "none",
                      transform: isActive ? "scale(1.1)" : "none",
                    }}
                  >
                    {isPassed ? "✓" : step.num}
                  </div>
                  <span
                    className="text-xs font-semibold mt-2.5 transition-colors"
                    style={{
                      color: isActive ? "var(--color-text)" : "var(--color-muted)",
                    }}
                  >
                    {step.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Active Step Feature Display Panel */}
        <ScrollReveal animation="fade-up" className="max-w-4xl mx-auto">
          <div
            className="p-6 sm:p-8 rounded-2xl border card-layer-shadow spotlight-card"
            style={{
              background: "var(--color-surface)",
              borderColor: "var(--color-border)",
            }}
          >
            <div className="grid grid-cols-12 gap-8 items-center">
              {/* Left narrative */}
              <div className="col-span-7">
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="text-xs font-mono font-bold px-2 py-0.5 rounded border"
                    style={{
                      background: "var(--color-bg)",
                      color: "var(--color-gold)",
                      borderColor: "var(--color-border)",
                    }}
                  >
                    Step {current.num} of 05
                  </span>
                  <Badge color="gold">{current.badge}</Badge>
                </div>

                <h3
                  className="text-xl sm:text-2xl font-bold mt-2"
                  style={{ color: "var(--color-text)" }}
                >
                  {current.title}
                </h3>

                <p
                  className="text-sm mt-3 leading-relaxed"
                  style={{ color: "var(--color-subtle)" }}
                >
                  {current.desc}
                </p>

                <div
                  className="mt-6 p-3.5 rounded-xl border text-xs"
                  style={{
                    background: "var(--color-bg)",
                    borderColor: "var(--color-border)",
                  }}
                >
                  <p className="font-semibold" style={{ color: "var(--color-gold)" }}>
                    {current.previewTitle}
                  </p>
                  <p className="mt-1" style={{ color: "var(--color-muted)" }}>
                    {current.previewDetail}
                  </p>
                </div>
              </div>

              {/* Right interactive visual simulation */}
              <div className="col-span-5 flex flex-col items-center justify-center p-6 rounded-xl border text-center"
                   style={{ background: "var(--color-bg-subtle)", borderColor: "var(--color-border)" }}>
                <span className="text-4xl mb-3">{current.icon}</span>

                {activeStep === 0 && (
                  <div className="w-full space-y-2 text-xs text-left">
                    <div className="p-2 rounded border bg-[var(--color-surface)] border-[var(--color-border)] flex justify-between items-center">
                      <span className="font-medium text-[var(--color-text)]">RemoteOK API</span>
                      <span className="text-[var(--color-green)] text-[0.7rem]">● Live Sync</span>
                    </div>
                    <div className="p-2 rounded border bg-[var(--color-surface)] border-[var(--color-border)] flex justify-between items-center">
                      <span className="font-medium text-[var(--color-text)]">YC Jobs Scraper</span>
                      <span className="text-[var(--color-green)] text-[0.7rem]">● Scraped</span>
                    </div>
                  </div>
                )}

                {activeStep === 1 && (
                  <div className="w-full space-y-2 text-xs text-left">
                    <p className="text-[0.7rem] uppercase font-bold text-[var(--color-muted)]">Extracted Stack:</p>
                    <div className="flex flex-wrap gap-1">
                      {["React", "TypeScript", "Python", "FastAPI", "PostgreSQL"].map((t) => (
                        <span key={t} className="px-2 py-0.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[0.7rem] text-[var(--color-gold)]">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {activeStep === 2 && (
                  <div className="flex flex-col items-center">
                    <ScoreRing score={91} size="lg" showLabel />
                    <p className="text-xs font-semibold mt-2 text-[var(--color-green)]">High Fit Alignment</p>
                  </div>
                )}

                {activeStep === 3 && (
                  <div className="w-full text-xs text-left space-y-1.5">
                    <p className="text-[0.7rem] font-bold text-[var(--color-gold)]">Suggested Prep Question:</p>
                    <p className="p-2 rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-subtle)] text-[0.72rem]">
                      &quot;How do you architect server-rendered React components with streaming responses?&quot;
                    </p>
                  </div>
                )}

                {activeStep === 4 && (
                  <div className="w-full grid grid-cols-2 gap-1.5 text-xs text-center">
                    <div className="p-1.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)]">
                      <span className="block text-[var(--color-muted)] text-[0.65rem]">Saved</span>
                      <span className="font-bold text-[var(--color-text)]">5</span>
                    </div>
                    <div className="p-1.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)]">
                      <span className="block text-[var(--color-sky)] text-[0.65rem]">Applied</span>
                      <span className="font-bold text-[var(--color-text)]">8</span>
                    </div>
                    <div className="p-1.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)]">
                      <span className="block text-[var(--color-amber)] text-[0.65rem]">Interview</span>
                      <span className="font-bold text-[var(--color-text)]">3</span>
                    </div>
                    <div className="p-1.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)]">
                      <span className="block text-[var(--color-green)] text-[0.65rem]">Offer</span>
                      <span className="font-bold text-[var(--color-text)]">1</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </ScrollReveal>
      </div>

      {/* Mobile Vertical Timeline (320px - 767px) */}
      <div className="md:hidden flex flex-col gap-4 relative">
        {WORKFLOW_STEPS.map((step, idx) => (
          <ScrollReveal key={step.num} animation="fade-up" delayMs={idx * 60}>
            <div
              className="p-5 rounded-xl border flex flex-col justify-between card-layer-shadow"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
              }}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{step.icon}</span>
                  <span
                    className="font-mono text-xs font-bold px-2 py-0.5 rounded border"
                    style={{
                      background: "var(--color-bg)",
                      color: "var(--color-gold)",
                      borderColor: "var(--color-border)",
                    }}
                  >
                    {step.num}
                  </span>
                </div>
                <Badge color="gold">{step.label}</Badge>
              </div>

              <h3 className="font-bold text-base mb-1.5" style={{ color: "var(--color-text)" }}>
                {step.title}
              </h3>
              <p className="text-xs leading-relaxed" style={{ color: "var(--color-subtle)" }}>
                {step.desc}
              </p>
            </div>
          </ScrollReveal>
        ))}
      </div>
    </section>
  );
}
