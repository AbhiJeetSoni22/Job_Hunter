"use client";

import { Card } from "@/components/ui/Card";
import { SkillChip } from "./SkillChip";
import { categorizeSkills, type SkillCategory } from "@/lib/categorizeSkills";
import type { Resume } from "@/lib/types";

interface ResumeSkillsCardProps {
  resume: Resume;
}

const CATEGORY_COLORS: Record<
  SkillCategory,
  { bg: string; text: string; border: string }
> = {
  Frontend: {
    bg: "rgba(56,189,248,0.1)",
    text: "var(--color-sky)",
    border: "rgba(56,189,248,0.25)",
  },
  Backend: {
    bg: "rgba(99,102,241,0.12)",
    text: "var(--color-accent-h)",
    border: "rgba(99,102,241,0.3)",
  },
  Database: {
    bg: "rgba(34,197,94,0.1)",
    text: "var(--color-green)",
    border: "rgba(34,197,94,0.25)",
  },
  Cloud: {
    bg: "rgba(245,158,11,0.1)",
    text: "var(--color-amber)",
    border: "rgba(245,158,11,0.25)",
  },
  "AI/ML": {
    bg: "rgba(168,85,247,0.12)",
    text: "#c084fc",
    border: "rgba(168,85,247,0.3)",
  },
  Other: {
    bg: "rgba(75,83,99,0.2)",
    text: "var(--color-subtle)",
    border: "rgba(75,83,99,0.35)",
  },
};

function SparklesIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
      <path d="M19 13l.75 2.25L22 16l-2.25.75L19 19l-.75-2.25L16 16l2.25-.75L19 13z" />
    </svg>
  );
}

export function ResumeSkillsCard({ resume }: ResumeSkillsCardProps) {
  const groups = categorizeSkills(resume.skills);

  return (
    <Card padding="none" className="card-elevated overflow-hidden fade-up-2">
      <div
        className="px-5 py-4 flex items-center justify-between gap-3"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        <div className="flex items-center gap-2.5">
          <span style={{ color: "var(--color-accent-h)" }}>
            <SparklesIcon />
          </span>
          <div>
            <h2
              className="text-sm font-semibold"
              style={{ color: "var(--color-text)" }}
            >
              Extracted Skills
            </h2>
            <p className="text-xs mt-0.5" style={{ color: "var(--color-subtle)" }}>
              {resume.skills.length} skill{resume.skills.length !== 1 ? "s" : ""}{" "}
              identified by Gemini AI
            </p>
          </div>
        </div>
      </div>

      <div className="p-5">
        {resume.skills.length === 0 ? (
          <p
            className="text-sm text-center py-8"
            style={{ color: "var(--color-muted)" }}
          >
            No skills were extracted from this resume.
          </p>
        ) : (
          <div className="space-y-5">
            {groups.map(({ category, skills }) => {
              const colors = CATEGORY_COLORS[category];
              return (
                <div key={category}>
                  <div className="flex items-center gap-2 mb-2.5">
                    <span
                      className="text-[0.65rem] font-semibold uppercase tracking-wider px-2 py-0.5 rounded"
                      style={{
                        color: colors.text,
                        background: colors.bg,
                        border: `1px solid ${colors.border}`,
                      }}
                    >
                      {category}
                    </span>
                    <span
                      className="text-[0.65rem]"
                      style={{ color: "var(--color-muted)" }}
                    >
                      {skills.length}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {skills.map((skill) => (
                      <SkillChip
                        key={skill}
                        skill={skill}
                        variant={category === "Other" ? "default" : "category"}
                        colors={colors}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}
