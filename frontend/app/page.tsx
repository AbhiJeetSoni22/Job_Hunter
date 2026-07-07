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
  { icon: "🤖", label: "AI-Powered Matching" },
  { icon: "🌐", label: "Multi-Source Job Discovery" },
  { icon: "📄", label: "Resume Skill Extraction" },
  { icon: "📊", label: "Application Tracking" },
];

const STEPS = [
  {
    n: "1",
    icon: "📎",
    title: "Upload Resume",
    desc: "Automatically extract skills and profile information with AI.",
  },
  {
    n: "2",
    icon: "🔄",
    title: "Sync Jobs",
    desc: "Aggregate internships and jobs from multiple sources in one place.",
  },
  {
    n: "3",
    icon: "⭐",
    title: "Get AI Matches",
    desc: "See personalized match scores and discover relevant opportunities.",
  },
];

const FEATURES = [
  {
    icon: "🧠",
    title: "AI Resume Analysis",
    desc: "Extracts skills automatically from your resume — no manual tagging.",
  },
  {
    icon: "🎯",
    title: "Smart Job Matching",
    desc: "Find opportunities relevant to your profile, ranked by fit.",
  },
  {
    icon: "📋",
    title: "Application Tracking",
    desc: "Track Saved, Applied, Interview, Offer, and Rejected in one workflow.",
  },
  {
    icon: "📈",
    title: "Dashboard Analytics",
    desc: "Monitor opportunities and match quality at a glance.",
  },
  {
    icon: "🌐",
    title: "Multi-Source Discovery",
    desc: "Jobs collected and de-duplicated from multiple providers.",
  },
  {
    icon: "✅",
    title: "Resume Validation",
    desc: "Prevents invalid uploads and improves matching quality.",
  },
];

const BENEFITS = [
  {
    icon: "⏱️",
    title: "Save Time",
    desc: "No manual searching across a dozen job boards.",
  },
  {
    icon: "🎯",
    title: "Better Opportunities",
    desc: "AI identifies roles that actually fit your skills.",
  },
  {
    icon: "🗂️",
    title: "Organized Workflow",
    desc: "Track every application stage in one dashboard.",
  },
  {
    icon: "🎓",
    title: "Career Focused",
    desc: "Built specifically for students and early-career freshers.",
  },
];

const PREVIEW_JOBS = [
  {
    company: "Nimbus Labs",
    role: "Frontend Intern",
    score: 92,
    status: "applied" as const,
  },
  {
    company: "Vectra AI",
    role: "ML Intern",
    score: 87,
    status: "saved" as const,
  },
  {
    company: "Corelogic",
    role: "SWE Intern",
    score: 74,
    status: "interview" as const,
  },
];

// ── Page ───────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <div className="flex flex-col gap-20 md:gap-28 pb-8">
      {/* ── 1. Hero ──────────────────────────────────────────────────── */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center pt-4">
        <div>
          <Badge color="indigo">AI-Powered Job Search</Badge>
          <h1
            className="mt-4 fade-up fade-up-1"
            style={{
              fontSize: "2.5rem",
              lineHeight: 1.15,
              fontWeight: 800,
              color: "var(--color-text)",
              letterSpacing: "-0.02em",
            }}
          >
            Find Better Internships Faster With AI
          </h1>
          <p
            className="mt-4 max-w-lg fade-up fade-up-2"
            style={{
              fontSize: "1.05rem",
              color: "var(--color-subtle)",
              lineHeight: 1.6,
            }}
          >
            Upload your resume, discover opportunities from multiple sources,
            and instantly see which jobs match your skills.
          </p>
          <div className="flex flex-wrap items-center gap-3 mt-7 fade-up fade-up-3">
            <Link href="/dashboard">
              <Button size="lg">Get Started</Button>
            </Link>
            <Link href="/jobs">
              <Button size="lg" variant="secondary">
                View Jobs
              </Button>
            </Link>
          </div>
        </div>

        {/* Hero visual — CSS-only mockup, no stock imagery */}
        <div className="relative fade-up fade-up-2">
          <div
            aria-hidden
            className="absolute -inset-8 rounded-full"
            style={{
              background:
                "radial-gradient(circle at 30% 20%, rgba(99,102,241,0.25), transparent 60%)",
              filter: "blur(10px)",
            }}
          />
          <Card padding="lg" className="relative">
            <p
              className="text-xs uppercase tracking-wide mb-4"
              style={{ color: "var(--color-muted)" }}
            >
              Match Score Preview
            </p>
            <div className="flex flex-col gap-3">
              {PREVIEW_JOBS.map((job) => (
                <div
                  key={job.company}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg"
                  style={{
                    background: "var(--color-bg)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  <div>
                    <p
                      style={{
                        fontWeight: 600,
                        fontSize: "0.875rem",
                        color: "var(--color-text)",
                      }}
                    >
                      {job.role}
                    </p>
                    <p
                      style={{
                        fontSize: "0.78rem",
                        color: "var(--color-subtle)",
                      }}
                    >
                      {job.company}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
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
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {VALUE_BAR.map((item) => (
            <Card key={item.label} padding="md" className="text-center">
              <div style={{ fontSize: "1.4rem" }}>{item.icon}</div>
              <p
                className="mt-2"
                style={{
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  color: "var(--color-subtle)",
                }}
              >
                {item.label}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* ── 3. How it works ──────────────────────────────────────────── */}
      <section>
        <h2
          className="text-center"
          style={{
            fontSize: "1.75rem",
            fontWeight: 700,
            color: "var(--color-text)",
          }}
        >
          How It Works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-8">
          {STEPS.map((step, i) => (
            <Card
              key={step.n}
              padding="lg"
              hoverable
              className={`relative fade-up fade-up-${i + 1}`}
            >
              <span
                className="absolute top-4 right-4"
                style={{
                  fontSize: "1.75rem",
                  fontWeight: 800,
                  color: "var(--color-border)",
                }}
              >
                {step.n}
              </span>
              <div style={{ fontSize: "1.5rem" }}>{step.icon}</div>
              <h3
                className="mt-3"
                style={{
                  fontSize: "1.05rem",
                  fontWeight: 700,
                  color: "var(--color-text)",
                }}
              >
                {step.title}
              </h3>
              <p
                className="mt-1.5"
                style={{ fontSize: "0.875rem", color: "var(--color-subtle)" }}
              >
                {step.desc}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* ── 4. Features ──────────────────────────────────────────────── */}
      <section>
        <h2
          className="text-center"
          style={{
            fontSize: "1.75rem",
            fontWeight: 700,
            color: "var(--color-text)",
          }}
        >
          Everything You Need To Land An Internship
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 mt-8">
          {FEATURES.map((f) => (
            <Card key={f.title} padding="lg" hoverable>
              <div style={{ fontSize: "1.4rem" }}>{f.icon}</div>
              <h3
                className="mt-3"
                style={{
                  fontSize: "1rem",
                  fontWeight: 700,
                  color: "var(--color-text)",
                }}
              >
                {f.title}
              </h3>
              <p
                className="mt-1.5"
                style={{ fontSize: "0.85rem", color: "var(--color-subtle)" }}
              >
                {f.desc}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* ── 5. Dashboard preview ─────────────────────────────────────── */}
      <section>
        <h2
          className="text-center"
          style={{
            fontSize: "1.75rem",
            fontWeight: 700,
            color: "var(--color-text)",
          }}
        >
          Your Job Search, At A Glance
        </h2>
        <p
          className="text-center max-w-xl mx-auto mt-2"
          style={{ color: "var(--color-subtle)", fontSize: "0.95rem" }}
        >
          One dashboard for match scores, top jobs, and search statistics.
        </p>

        <Card padding="lg" className="mt-8 fade-up">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
            <PreviewStat label="Total Jobs" value="164" icon="💼" />
            <PreviewStat
              label="Top Match"
              value="92%"
              icon="⭐"
              valueColor="var(--color-green)"
            />
            <PreviewStat label="Average Match" value="71%" icon="📊" />
            <PreviewStat label="Applications" value="12" icon="📨" />
          </div>
          <div className="flex flex-col gap-2">
            {PREVIEW_JOBS.map((job) => (
              <div
                key={job.company}
                className="flex items-center justify-between gap-3 p-3 rounded-lg card-hover"
                style={{
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <div>
                  <p
                    style={{
                      fontWeight: 600,
                      fontSize: "0.875rem",
                      color: "var(--color-text)",
                    }}
                  >
                    {job.role} · {job.company}
                  </p>
                </div>
                <div className="flex items-center gap-2">
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
        <h2
          className="text-center"
          style={{
            fontSize: "1.75rem",
            fontWeight: 700,
            color: "var(--color-text)",
          }}
        >
          Why Internship Hunter?
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mt-8">
          {BENEFITS.map((b) => (
            <div key={b.title}>
              <div style={{ fontSize: "1.4rem" }}>{b.icon}</div>
              <h3
                className="mt-2"
                style={{
                  fontSize: "0.95rem",
                  fontWeight: 700,
                  color: "var(--color-text)",
                }}
              >
                {b.title}
              </h3>
              <p
                className="mt-1"
                style={{ fontSize: "0.83rem", color: "var(--color-subtle)" }}
              >
                {b.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── 7. Application tracking ──────────────────────────────────── */}
      <section>
        <h2
          className="text-center"
          style={{
            fontSize: "1.75rem",
            fontWeight: 700,
            color: "var(--color-text)",
          }}
        >
          Manage Every Application Stage
        </h2>
        <p
          className="text-center max-w-xl mx-auto mt-2"
          style={{ color: "var(--color-subtle)", fontSize: "0.95rem" }}
        >
          Move jobs through your pipeline with a single click — from first save
          to final offer.
        </p>

        <Card padding="lg" className="mt-8">
          <div className="flex flex-wrap items-center justify-center gap-3">
            <StatusBadge status="saved" />
            <Arrow />
            <StatusBadge status="applied" />
            <Arrow />
            <StatusBadge status="interview" />
            <Arrow />
            <StatusBadge status="offer" />
          </div>
          <div className="flex items-center justify-center gap-3 mt-4">
            <span style={{ fontSize: "0.78rem", color: "var(--color-muted)" }}>
              or, at any stage after applying
            </span>
            <Arrow />
            <StatusBadge status="rejected" />
          </div>
        </Card>
      </section>

      {/* ── 8. Final CTA ─────────────────────────────────────────────── */}
      <section>
        <Card padding="lg" className="text-center py-10 fade-up">
          <h2
            style={{
              fontSize: "1.75rem",
              fontWeight: 700,
              color: "var(--color-text)",
            }}
          >
            Ready to Find Your Next Opportunity?
          </h2>
          <p
            className="max-w-md mx-auto mt-2"
            style={{ color: "var(--color-subtle)", fontSize: "0.95rem" }}
          >
            Start matching your skills with internships and jobs in minutes.
          </p>
          <div className="mt-6">
            <Link href="/dashboard">
              <Button size="lg">Get Started</Button>
            </Link>
          </div>
        </Card>
      </section>

      {/* ── 9. In-page footer summary ────────────────────────────────── */}
      <section
        className="pt-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
        style={{ borderTop: "1px solid var(--color-border)" }}
      >
        <div>
          <p style={{ fontWeight: 700, color: "var(--color-text)" }}>
            Internship Hunter
          </p>
          <p
            className="mt-1 max-w-sm"
            style={{ fontSize: "0.8rem", color: "var(--color-subtle)" }}
          >
            AI-powered internship discovery and job matching platform.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard"
            style={{ fontSize: "0.85rem", color: "var(--color-subtle)" }}
          >
            Dashboard
          </Link>
          <Link
            href="/jobs"
            style={{ fontSize: "0.85rem", color: "var(--color-subtle)" }}
          >
            Jobs
          </Link>
          <Link
            href="/resume"
            style={{ fontSize: "0.85rem", color: "var(--color-subtle)" }}
          >
            Resume
          </Link>
        </div>
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
        style={{
          fontSize: "0.68rem",
          color: "var(--color-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        {icon} {label}
      </p>
      <p
        className="mt-1"
        style={{
          fontSize: "1.2rem",
          fontWeight: 700,
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
    <span style={{ color: "var(--color-muted)", fontSize: "1rem" }} aria-hidden>
      →
    </span>
  );
}
