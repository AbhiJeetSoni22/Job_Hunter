"use client";

import { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { JobDescriptionForm } from "@/components/resume-review/JobDescriptionForm";
import { MatchScoreCard } from "@/components/resume-review/MatchScoreCard";
import { SkillTagSection } from "@/components/resume-review/SkillTagSection";
import { BulletListSection } from "@/components/resume-review/BulletListSection";
import { analyzeResume, ApiClientError } from "@/lib/api";
import type { ResumeAnalysisResponse } from "@/lib/types";

export default function ResumeReviewPage() {
  const [result, setResult] = useState<ResumeAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [noResume, setNoResume] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(jobDescription: string) {
    if (loading) return;

    const trimmed = jobDescription.trim();
    if (!trimmed) {
      setValidationError("Please enter a job description.");
      return;
    }

    setValidationError(null);
    setErrorMessage(null);
    setNoResume(false);
    setLoading(true);

    try {
      const analysis = await analyzeResume(trimmed);
      setResult(analysis);
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.code === "NO_RESUME") {
          setNoResume(true);
        } else if (err.code === "EMPTY_JOB_DESCRIPTION") {
          setValidationError(err.message || "Please enter a job description.");
        } else if (err.code === "ANALYSIS_ERROR") {
          setErrorMessage(
            err.message || "Resume analysis failed. Please try again.",
          );
        } else {
          setErrorMessage(
            err.message || "Something went wrong. Please try again.",
          );
        }
      } else {
        setErrorMessage("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <PageHeader
        title="Resume Gap Analyzer"
        subtitle="Analyze your uploaded resume against a job description and receive personalized recommendations."
      />

      {noResume ? (
        <EmptyState
          icon="📎"
          title="No resume on file"
          description="Upload a resume before running analysis."
          action={
            <Link href="/resume">
              <Button variant="primary" size="sm">
                Go to Resume
              </Button>
            </Link>
          }
        />
      ) : (
        <>
          <JobDescriptionForm
            loading={loading}
            validationError={validationError}
            onSubmit={handleSubmit}
          />

          {errorMessage && (
            <div className="mt-4">
              <ErrorState title="Analysis failed" message={errorMessage} />
            </div>
          )}

          {result && (
            <div className="mt-6 flex flex-col gap-4">
              <MatchScoreCard
                score={result.match_score}
                summary={result.summary}
              />

              <SkillTagSection
                title="Missing Skills"
                skills={result.missing_skills}
                missing
                emptyMessage="No missing skills detected."
                animationClass="fade-up fade-up-2"
              />

              <SkillTagSection
                title="Strengths"
                skills={result.strengths}
                emptyMessage="No matching strengths detected."
                animationClass="fade-up fade-up-3"
              />

              <BulletListSection
                title="Suggestions"
                items={result.suggestions}
                emptyMessage="No suggestions available."
                animationClass="fade-up fade-up-4"
              />

              <BulletListSection
                title="ATS Tips"
                items={result.ats_tips}
                emptyMessage="No ATS tips available."
                animationClass="fade-up fade-up-4"
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
