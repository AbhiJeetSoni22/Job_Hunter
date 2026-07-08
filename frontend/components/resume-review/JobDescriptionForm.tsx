"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

interface JobDescriptionFormProps {
  initialValue?: string; // future prefill hook, unused for now
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
    <Card padding="md" className="fade-up fade-up-1">
      <label
        htmlFor="job-description"
        style={{
          fontSize: "0.75rem",
          fontWeight: 700,
          color: "var(--color-subtle)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}
        className="mb-2 block"
      >
        Job Description
      </label>
      <textarea
        id="job-description"
        value={jobDescription}
        onChange={(e) => setJobDescription(e.target.value)}
        placeholder="Paste the job description here…"
        rows={8}
        style={{
          width: "100%",
          background: "var(--color-bg)",
          border: "1px solid var(--color-border)",
          borderRadius: "0.5rem",
          padding: "0.75rem",
          fontSize: "0.875rem",
          color: "var(--color-text)",
          resize: "vertical",
        }}
      />
      {validationError && (
        <p
          style={{ color: "var(--color-red)", fontSize: "0.8rem" }}
          className="mt-2"
        >
          {validationError}
        </p>
      )}
      <div className="mt-4">
        <Button
          variant="primary"
          loading={loading}
          disabled={loading}
          onClick={() => onSubmit(jobDescription)}
        >
          {loading ? "Analyzing Resume…" : "Analyze Resume"}
        </Button>
      </div>
    </Card>
  );
}
