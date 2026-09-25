import type { Metadata } from "next";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { StatusBadge } from "@/components/jobs/StatusBadge";
import { ScoreBadge } from "@/components/jobs/ScoreBadge";

export const metadata: Metadata = {
  title: { absolute: "Internship Hunter – AI-Powered Internship Discovery" },
  description:
    "Upload your resume, discover opportunities, and find the best internships with AI-powered matching.",
};

// ── Static content ───────────────────────────────────────────────────────────

const VALUE_BAR = [
  { icon: "⚡", label: "AI-Powered Matching" },
  { icon: "🌐", label: "Multi-Source Job Discovery" },
  { icon: "📄", label: "Resume Skill Extraction" },
  { icon: "📊", label: "Application Tracking" },
];

const STEPS = [
  {
    n: "01",
    icon: "📎",
    title: "Upload Resume",
    desc: "Automatically extract skills and profile information using Gemini AI.",
  },
  {
    n: "02",
    icon: "🔄",
    title: "Sync Jobs",
    desc: "Aggregate internships and jobs from multiple sources in one place.",
  },
  {
    n: "03",
    icon: "⭐",
    title: "Get AI Matches",
    desc: "See personalized match scores and discover relevant opportunities ranked by fit.",
  },
];

const FEATURES = [
  {
    icon: "🧠",
    title: "AI Resume Analysis",
    desc: "Extracts skills automatically from your resume — no tedious manual tagging.",
  },
  {
    icon: "🎯",
    title: "Smart Job Matching",
    desc: "Find opportunities tailored to your skill profile, scored and ranked by fit.",
  },
  {
    icon: "📋",
    title: "Application Tracking",
    desc: "Track Saved, Applied, Interview, Offer, and Rejected in a unified workflow.",
  },
  {
    icon: "📈",
    title: "Dashboard Analytics",
    desc: "Monitor your candidate pipeline and match quality at a single glance.",
  },
  {
    icon: "🌐",
    title: "Multi-Source Discovery",
    desc: "Fresh internships collected and de-duplicated from leading tech boards.",
  },
  {
    icon: "✨",
    title: "Interview Prep & ATS",
    desc: "Generate targeted technical & behavioral interview questions on demand.",
  },
];

const BENEFITS = [
  {
    icon: "⏱️",
    title: "Save Time",
    desc: "No manual scouring across dozens of disparate job boards.",
  },
  {
    icon: "🎯",
    title: "Better Opportunities",
    desc: "AI identifies roles that truly fit your technical skills.",
  },
  {
    icon: "🗂️",
    title: "Organized Workflow",
    desc: "Track every application stage in one unified workspace.",
  },
  {
    icon: "🎓",
    title: "Career Focused",
    desc: "Built specifically for students, freshers, and early-career engineers.",
  },
];

const PREVIEW_JOBS = [
  {
    company: "Nimbus Labs",
    role: "Frontend Engineer Intern",
    score: 94,
    status: "applied" as const,
  },
  {
    company: "Vectra AI",
    role: "Machine Learning Intern",
    score: 88,
    status: "saved" as const,
  },
  {
    company: "Corelogic",
    role: "Software Engineer Intern",
    score: 76,
    status: "interview" as const,
  },
];

// ── Page ───────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <div className="flex flex-col gap-16 sm:gap-24 pb-12">
      {/* ── 1. Hero ──────────────────────────────────────────────────── */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-8 sm:gap-12 items-center pt-2 sm:pt-6">
        <div>
          <Badge color="indigo">AI-Powered Job Platform</Badge>
          <h1
            className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight leading-[1.12] fade-up fade-up-1"
            style={{ color: "var(--color-text)" }}
          >
            Find Better Internships <span style={{ color: "var(--color-gold)" }}>Faster</span> With AI
          </h1>
          <p
            className="mt-4 max-w-lg text-sm sm:text-base leading-relaxed fade-up fade-up-2"
            style={{ color: "var(--color-subtle)" }}
          >
            Upload your resume, aggregate opportunities from multiple sources,
            and instantly see which engineering roles match your exact skills.
          </p>
          <div className="flex flex-wrap items-center gap-3 mt-7 fade-up fade-up-3">
            <Link href="/dashboard" className="w-full xs:w-auto">
              <Button size="lg" className="w-full xs:w-auto">
                Get Started
              </Button>
            </Link>
            <Link href="/jobs" className="w-full xs:w-auto">
              <Button size="lg" variant="secondary" className="w-full xs:w-auto">
                View Jobs
              </Button>
            </Link>
          </div>
        </div>

        {/* Hero visual — CSS-only mockup */}
        <div className="relative fade-up fade-up-2 w-full max-w-lg mx-auto lg:max-w-none">
          <div
            aria-hidden
            className="absolute -inset-4 sm:-inset-8 rounded-full pointer-events-none"
            style={{
              background:
                "radial-gradient(circle at 40% 30%, rgba(143, 23, 51, 0.18), transparent 70%)",
              filter: "blur(24px)",
            }}
          />
          <Card padding="lg" className="relative card-elevated" style={{ borderColor: "var(--color-border)" }}>
            <div className="flex items-center justify-between mb-4">
              <p
                className="text-[0.7rem] uppercase tracking-wider font-semibold"
                style={{ color: "var(--color-muted)" }}
              >
                Match Score Preview
              </p>
              <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: "var(--color-green)" }} />
            </div>

            <div className="flex flex-col gap-2.5">
              {PREVIEW_JOBS.map((job) => (
                <div
                  key={job.company}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-3 p-3 rounded-lg"
                  style={{
                    background: "var(--color-bg)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  <div className="min-w-0">
                    <p
                      className="font-semibold text-sm truncate"
                      style={{ color: "var(--color-text)" }}
                    >
                      {job.role}
                    </p>
                    <p
                      className="text-xs truncate mt-0.5"
                      style={{ color: "var(--color-subtle)" }}
                    >
                      {job.company}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0 self-start sm:self-auto">
                    <StatusBadge status={job.status} />
                    <ScoreBadge score={job.score} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </section>

      {/* ── 2. Trust / value bar ─────────────────────────────────────── */}
      <section>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
          {VALUE_BAR.map((item) => (
            <Card key={item.label} padding="md" className="text-center">
              <div className="text-xl sm:text-2xl">{item.icon}</div>
              <p
                className="mt-2 text-xs sm:text-sm font-semibold truncate"
                style={{ color: "var(--color-subtle)" }}
              >
                {item.label}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* ── 3. How it works ──────────────────────────────────────────── */}
      <section>
        <div className="text-center max-w-xl mx-auto mb-8 sm:mb-10">
          <p className="text-xs uppercase tracking-wider font-semibold mb-2" style={{ color: "var(--color-gold)" }}>
            Workflow
          </p>
          <h2
            className="text-2xl sm:text-3xl font-bold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            How It Works
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
          {STEPS.map((step, i) => (
            <Card
              key={step.n}
              padding="lg"
              hoverable
              className={`relative fade-up fade-up-${i + 1}`}
            >
              <span
                className="absolute top-4 right-4 font-mono font-bold text-lg select-none"
                style={{ color: "var(--color-border-hover)" }}
              >
                {step.n}
              </span>
              <div className="text-2xl">{step.icon}</div>
              <h3
                className="mt-3 text-base sm:text-lg font-bold"
                style={{ color: "var(--color-text)" }}
              >
                {step.title}
              </h3>
              <p
                className="mt-1.5 text-xs sm:text-sm leading-relaxed"
                style={{ color: "var(--color-subtle)" }}
              >
                {step.desc}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* ── 4. Features ──────────────────────────────────────────────── */}
      <section>
        <div className="text-center max-w-xl mx-auto mb-8 sm:mb-10">
          <p className="text-xs uppercase tracking-wider font-semibold mb-2" style={{ color: "var(--color-gold)" }}>
            Capabilities
          </p>
          <h2
            className="text-2xl sm:text-3xl font-bold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            Engineered For Technical Job Searches
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          {FEATURES.map((f) => (
            <Card key={f.title} padding="lg" hoverable>
              <div className="text-xl sm:text-2xl">{f.icon}</div>
              <h3
                className="mt-3 text-sm sm:text-base font-bold"
                style={{ color: "var(--color-text)" }}
              >
                {f.title}
              </h3>
              <p
                className="mt-1.5 text-xs sm:text-sm leading-relaxed"
                style={{ color: "var(--color-subtle)" }}
              >
                {f.desc}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* ── 5. Dashboard preview ─────────────────────────────────────── */}
      <section>
        <div className="text-center max-w-xl mx-auto mb-8 sm:mb-10">
          <h2
            className="text-2xl sm:text-3xl font-bold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            Your Job Search, At A Glance
          </h2>
          <p
            className="mt-2 text-xs sm:text-sm"
            style={{ color: "var(--color-subtle)" }}
          >
            One centralized cockpit for match scores, scored listings, and status analytics.
          </p>
        </div>

        <Card padding="lg" className="fade-up card-elevated">
          <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-5">
            <PreviewStat label="Total Jobs" value="164" icon="💼" />
            <PreviewStat
              label="Top Match"
              value="94%"
              icon="⭐"
              valueColor="var(--color-green)"
            />
            <PreviewStat label="Average Match" value="73%" icon="📊" />
            <PreviewStat label="Applications" value="12" icon="📨" />
          </div>
          <div className="flex flex-col gap-2">
            {PREVIEW_JOBS.map((job) => (
              <div
                key={job.company}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg card-hover"
                style={{
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <p
                  className="font-semibold text-xs sm:text-sm"
                  style={{ color: "var(--color-text)" }}
                >
                  {job.role} <span style={{ color: "var(--color-muted)" }}>· {job.company}</span>
                </p>
                <div className="flex items-center gap-2 self-start sm:self-auto flex-shrink-0">
                  <StatusBadge status={job.status} />
                  <ScoreBadge score={job.score} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </section>

      {/* ── 6. Benefits ──────────────────────────────────────────────── */}
      <section>
        <div className="text-center max-w-xl mx-auto mb-8 sm:mb-10">
          <h2
            className="text-2xl sm:text-3xl font-bold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            Why Internship Hunter?
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {BENEFITS.map((b) => (
            <Card key={b.title} padding="md" className="h-full">
              <div className="text-xl sm:text-2xl">{b.icon}</div>
              <h3
                className="mt-2.5 text-sm sm:text-base font-bold"
                style={{ color: "var(--color-text)" }}
              >
                {b.title}
              </h3>
              <p
                className="mt-1 text-xs sm:text-sm leading-relaxed"
                style={{ color: "var(--color-subtle)" }}
              >
                {b.desc}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* ── 7. Application tracking ──────────────────────────────────── */}
      <section>
        <div className="text-center max-w-xl mx-auto mb-8">
          <h2
            className="text-2xl sm:text-3xl font-bold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            Manage Every Application Stage
          </h2>
          <p
            className="mt-2 text-xs sm:text-sm"
            style={{ color: "var(--color-subtle)" }}
          >
            Move jobs through your pipeline with a single click — from initial save to final offer.
          </p>
        </div>

        <Card padding="lg" className="text-center">
          <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3 py-2">
            <StatusBadge status="saved" />
            <Arrow />
            <StatusBadge status="applied" />
            <Arrow />
            <StatusBadge status="interview" />
            <Arrow />
            <StatusBadge status="offer" />
          </div>
          <div className="flex items-center justify-center gap-2 mt-4 pt-4 border-t" style={{ borderColor: "var(--color-border)" }}>
            <span className="text-xs" style={{ color: "var(--color-muted)" }}>
              or, at any stage:
            </span>
            <Arrow />
            <StatusBadge status="rejected" />
          </div>
        </Card>
      </section>

      {/* ── 8. Final CTA ─────────────────────────────────────────────── */}
      <section>
        <Card
          padding="lg"
          className="text-center py-10 sm:py-12 relative overflow-hidden card-elevated"
          style={{
            borderColor: "var(--color-accent-border)",
            background: "linear-gradient(180deg, var(--color-surface) 0%, rgba(143, 23, 51, 0.08) 100%)",
          }}
        >
          <h2
            className="text-2xl sm:text-3xl font-bold tracking-tight"
            style={{ color: "var(--color-text)" }}
          >
            Ready to Find Your Next Opportunity?
          </h2>
          <p
            className="max-w-md mx-auto mt-2 text-xs sm:text-sm leading-relaxed"
            style={{ color: "var(--color-subtle)" }}
          >
            Upload your resume and start discovering matching internships in minutes.
          </p>
          <div className="mt-6 flex justify-center">
            <Link href="/dashboard">
              <Button size="lg">Get Started Free</Button>
            </Link>
          </div>
        </Card>
      </section>
    </div>
  );
}

// ── Local presentational helpers ────────────────────────────────────────────

function PreviewStat({
  label,
  value,
  icon,
  valueColor,
}: {
  label: string;
  value: string;
  icon: string;
  valueColor?: string;
}) {
  return (
    <div
      className="p-3 rounded-lg"
      style={{
        background: "var(--color-bg)",
        border: "1px solid var(--color-border)",
      }}
    >
      <p
        className="text-[0.68rem] uppercase tracking-wider font-semibold truncate"
        style={{ color: "var(--color-muted)" }}
      >
        {icon} {label}
      </p>
      <p
        className="mt-1 text-lg sm:text-xl font-bold"
        style={{
          color: valueColor ?? "var(--color-text)",
        }}
      >
        {value}
      </p>
    </div>
  );
}

function Arrow() {
  return (
    <span style={{ color: "var(--color-muted)", fontSize: "0.875rem" }} aria-hidden>
      →
    </span>
  );
}
