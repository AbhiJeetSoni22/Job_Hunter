"use client";

import type { RefObject } from "react";
import { Card } from "@/components/ui/Card";
import { ResumeUploader, type ResumeUploaderHandle } from "./ResumeUploader";

interface ResumeUploadCardProps {
  onFileSelected: (file: File) => void;
  loading?: boolean;
  uploaderRef?: RefObject<ResumeUploaderHandle | null>;
  variant?: "primary" | "replace";
}

const REQUIREMENTS = [
  { label: "PDF only", icon: "📄" },
  { label: "Max 5 MB", icon: "💾" },
  { label: "Max 3 pages", icon: "📑" },
] as const;

export function ResumeUploadCard({
  onFileSelected,
  loading = false,
  uploaderRef,
  variant = "primary",
}: ResumeUploadCardProps) {
  const isReplace = variant === "replace";

  return (
    <Card padding="none" className="card-elevated overflow-hidden fade-up">
      <div
        className="px-5 py-4"
        style={{
          borderBottom: "1px solid var(--color-border)",
          background:
            "linear-gradient(135deg, rgba(99,102,241,0.08) 0%, transparent 60%)",
        }}
      >
        <h2
          className="text-sm font-semibold"
          style={{ color: "var(--color-text)" }}
        >
          {isReplace ? "Replace Resume" : "Upload Resume"}
        </h2>
        <p className="text-xs mt-0.5" style={{ color: "var(--color-subtle)" }}>
          {isReplace
            ? "Upload a new PDF to replace your current profile."
            : "Drag and drop your resume or browse from your device."}
        </p>
      </div>

      <div className="p-5">
        <ResumeUploader
          ref={uploaderRef}
          onFileSelected={onFileSelected}
          loading={loading}
        />

        <div className="mt-4 grid grid-cols-3 gap-2">
          {REQUIREMENTS.map(({ label, icon }) => (
            <div
              key={label}
              className="flex flex-col items-center gap-1 px-2 py-2.5 rounded-lg text-center"
              style={{
                background: "var(--color-bg)",
                border: "1px solid var(--color-border)",
              }}
            >
              <span className="text-base" aria-hidden="true">
                {icon}
              </span>
              <span
                className="text-[0.65rem] font-medium leading-tight"
                style={{ color: "var(--color-subtle)" }}
              >
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
