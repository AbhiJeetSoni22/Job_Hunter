"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import { JobDescriptionForm } from "@/components/resume-review/JobDescriptionForm";
import { MatchScoreCard } from "@/components/resume-review/MatchScoreCard";
import { SkillTagSection } from "@/components/resume-review/SkillTagSection";
import { BulletListSection } from "@/components/resume-review/BulletListSection";
import { analyzeResume, getResume, ApiClientError } from "@/lib/api";
import type { ResumeAnalysisResponse } from "@/lib/types";

export default function ResumeReviewPage() {
  const [result, setResult] = useState<ResumeAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [noResume, setNoResume] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // ── Resume pre-check ──────────────────────────────────────────────────────
  // Same source of truth as the Dashboard/Resume page (getResume() → null
  // when no active resume). Checked on mount so the page gates itself
  // before the user ever pastes a JD, instead of surfacing NO_RESUME only
  // after they click Analyze.
  const [checkingResume, setCheckingResume] = useState(true);

  const checkResume = useCallback(async () => {
    setCheckingResume(true);
    try {
      const resume = await getResume();
      setNoResume(resume === null);
    } catch {
      // Fetch failure: fall back to letting the form render — the existing
      // NO_RESUME handling on submit still catches the no-resume case.
      setNoResume(false);
    } finally {
      setCheckingResume(false);
    }
  }, []);

  useEffect(() => {
    checkResume();
  }, [checkResume]);

  async function handleSubmit(jobDescription: string) {
    if (loading) return; // prevent duplicate submissions

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
          // NETWORK_ERROR, TIMEOUT, INVALID_RESPONSE, UNKNOWN_ERROR, etc.
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

      {checkingResume ? (
        <Card padding="lg">
          <div className="flex flex-col items-center gap-3 py-6">
            <Skeleton width="40%" height="1rem" />
            <Skeleton width="60%" height="0.8rem" />
            <Skeleton width="8rem" height="2rem" rounded="0.375rem" />
          </div>
        </Card>
      ) : noResume ? (
        <EmptyState
          icon="📎"
          title="Resume Required"
          description="Upload a resume before using Resume Gap Analyzer."
          action={
            <Link href="/resume">
              <Button variant="primary" size="sm">
                Upload Resume
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
