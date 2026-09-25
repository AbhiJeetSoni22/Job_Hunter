"use client";

import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

interface ResumeEmptyPanelProps {
  onUploadClick: () => void;
}

const FEATURES = [
  { icon: "🎯", title: "AI Job Matching", desc: "Score every listing against your skills" },
  { icon: "📊", title: "Resume Gap Analysis", desc: "See what's missing for any role" },
  { icon: "✨", title: "ATS Suggestions", desc: "Optimize for applicant tracking systems" },
  { icon: "🚀", title: "Internship Recommendations", desc: "Surface your best-fit opportunities" },
] as const;

export function ResumeEmptyPanel({ onUploadClick }: ResumeEmptyPanelProps) {
  return (
    <Card
      padding="none"
      className="card-elevated overflow-hidden fade-up-1 h-full"
    >
      <div
        className="px-5 sm:px-6 py-8 sm:py-10 text-center"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% 0%, rgba(143, 23, 51, 0.12) 0%, transparent 70%)",
        }}
      >
        <div
          className="w-14 h-14 mx-auto rounded-xl flex items-center justify-center text-2xl mb-4"
          style={{
            background: "var(--color-accent-subtle)",
            border: "1px solid var(--color-accent-border)",
            boxShadow: "0 0 30px -5px rgba(143, 23, 51, 0.35)",
          }}
        >
          🎯
        </div>

        <h2
          className="text-lg sm:text-xl font-bold tracking-tight"
          style={{ color: "var(--color-text)" }}
        >
          Upload Your Resume
        </h2>
        <p
          className="text-xs sm:text-sm mt-2 max-w-sm mx-auto leading-relaxed"
          style={{ color: "var(--color-subtle)" }}
        >
          Upload your resume to unlock AI-powered match scoring, gap analysis, and tailored interview preparation.
        </p>

        <Button
          variant="primary"
          size="md"
          className="mt-6"
          onClick={onUploadClick}
        >
          Upload Resume Now
        </Button>
      </div>

      <div
        className="px-4 sm:px-5 py-4 sm:py-5 grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3"
        style={{ borderTop: "1px solid var(--color-border)" }}
      >
        {FEATURES.map(({ icon, title, desc }) => (
          <div
            key={title}
            className="flex items-start gap-3 p-3 rounded-lg"
            style={{
              background: "var(--color-bg)",
              border: "1px solid var(--color-border)",
            }}
          >
            <span className="text-base sm:text-lg flex-shrink-0" aria-hidden="true">
              {icon}
            </span>
            <div className="min-w-0">
              <p
                className="text-xs sm:text-sm font-semibold truncate"
                style={{ color: "var(--color-text)" }}
              >
                {title}
              </p>
              <p
                className="text-xs mt-0.5 leading-relaxed"
                style={{ color: "var(--color-muted)" }}
              >
                {desc}
              </p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
