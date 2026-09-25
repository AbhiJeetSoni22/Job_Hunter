"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

interface JobDescriptionFormProps {
  initialValue?: string;
  loading: boolean;
  validationError: string | null;
  onSubmit: (jobDescription: string) => void;
}

export function JobDescriptionForm({
  initialValue = "",
  loading,
  validationError,
  onSubmit,
}: JobDescriptionFormProps) {
  const [jobDescription, setJobDescription] = useState(initialValue);

  return (
    <Card padding="lg" className="card-elevated fade-up fade-up-1">
      <label
        htmlFor="job-description"
        style={{
          fontSize: "0.72rem",
          fontWeight: 700,
          color: "var(--color-gold)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
        className="mb-2.5 block"
      >
        Target Job Description
      </label>
      <textarea
        id="job-description"
        value={jobDescription}
        onChange={(e) => setJobDescription(e.target.value)}
        placeholder="Paste the target job description or requirements here to analyze skill gaps…"
        rows={8}
        style={{
          width: "100%",
          background: "var(--color-bg)",
          border: "1px solid var(--color-border)",
          borderRadius: "0.5rem",
          padding: "0.85rem",
          fontSize: "0.875rem",
          color: "var(--color-text)",
          resize: "vertical",
          lineHeight: 1.6,
        }}
        className="focus:outline-none focus:border-[var(--color-gold)] transition-colors"
      />
      {validationError && (
        <p
          style={{ color: "var(--color-red)", fontSize: "0.8rem" }}
          className="mt-2"
        >
          {validationError}
        </p>
      )}
      <div className="mt-4 flex justify-end">
        <Button
          variant="primary"
          loading={loading}
          disabled={loading || !jobDescription.trim()}
          onClick={() => onSubmit(jobDescription)}
          className="w-full sm:w-auto"
        >
          {loading ? "Analyzing Resume Profile…" : "Analyze Resume Match"}
        </Button>
      </div>
    </Card>
  );
}
