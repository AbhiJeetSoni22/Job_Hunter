"use client";

import { BulletListSection } from "@/components/resume-review/BulletListSection";
import type { InterviewPrepResponse } from "@/lib/types";

interface InterviewPrepPanelProps {
  result: InterviewPrepResponse;
}

/**
 * Renders AI Interview Prep results as a stack of bullet-list sections,
 * inline within the Job Details page (Card section pattern — no new
 * page, no new modal primitive). Reuses the exact BulletListSection
 * component already used by the Resume Gap Analyzer for visual
 * consistency.
 */
export function InterviewPrepPanel({ result }: InterviewPrepPanelProps) {
  return (
    <div className="flex flex-col gap-3">
      <BulletListSection
        title="Resume / Project Questions"
        items={result.project_questions}
        emptyMessage="No resume/project questions generated."
      />
      <BulletListSection
        title="Technical Questions"
        items={result.technical_questions}
        emptyMessage="No technical questions generated."
      />
      <BulletListSection
        title="Behavioral Questions"
        items={result.behavioral_questions}
        emptyMessage="No behavioral questions generated."
      />
      <BulletListSection
        title="Topics To Revise"
        items={result.topics_to_revise}
        emptyMessage="No topics to revise generated."
      />
      <BulletListSection
        title="Interview Tips"
        items={result.interview_tips}
        emptyMessage="No interview tips generated."
      />
    </div>
  );
}
