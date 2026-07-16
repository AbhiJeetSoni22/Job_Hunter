"use client";

import { useEffect, useRef, useState } from "react";
import { Card } from "@/components/ui/Card";

const UPLOAD_STEPS = [
  { icon: "📄", label: "Uploading Resume" },
  { icon: "🔍", label: "Validating PDF" },
  { icon: "📝", label: "Extracting Content" },
  { icon: "🧠", label: "Analyzing Skills with Gemini" },
  { icon: "💾", label: "Building Resume Profile" },
  { icon: "✅", label: "Finalizing" },
] as const;

const STEP_INTERVAL_MS = 1_500;
const SUCCESS_DISMISS_MS = 2_000;
const COMPLETE_STAGGER_MS = 50;

type StepState = "completed" | "active" | "pending" | "failed";

export interface ResumeUploadProgressProps {
  status: "uploading" | "success" | "error";
  filename?: string;
  errorMessage?: string;
  onDismiss?: () => void;
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path
        d="M2.5 6L5 8.5L9.5 4"
        stroke="white"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path
        d="M3 3L9 9M9 3L3 9"
        stroke="white"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}

function AgentIcon() {
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
      <path d="M12 8V4H8" />
      <rect x="4" y="8" width="16" height="12" rx="2" />
      <path d="M2 14h2M20 14h2M9 13v2M15 13v2" />
    </svg>
  );
}

function getStepState(
  index: number,
  activeIndex: number,
  status: ResumeUploadProgressProps["status"],
): StepState {
  if (status === "success") {
    return index <= activeIndex ? "completed" : "pending";
  }
  if (status === "error") {
    if (index < activeIndex) return "completed";
    if (index === activeIndex) return "failed";
    return "pending";
  }
  if (index < activeIndex) return "completed";
  if (index === activeIndex) return "active";
  return "pending";
}

function connectorColor(
  index: number,
  activeIndex: number,
  status: ResumeUploadProgressProps["status"],
): string {
  if (status === "success") {
    return index < activeIndex ? "rgba(34, 197, 94, 0.4)" : "var(--color-border)";
  }
  if (status === "error") {
    if (index < activeIndex) return "rgba(34, 197, 94, 0.4)";
    if (index === activeIndex) return "rgba(239, 68, 68, 0.4)";
    return "var(--color-border)";
  }
  if (index < activeIndex) return "rgba(34, 197, 94, 0.4)";
  return "var(--color-border)";
}

function StepNode({
  state,
  icon,
}: {
  state: StepState;
  icon: string;
}) {
  if (state === "completed") {
    return (
      <div
        className="upload-step-check flex-shrink-0 flex items-center justify-center"
        style={{
          width: "1.75rem",
          height: "1.75rem",
          borderRadius: "9999px",
          background: "var(--color-green)",
        }}
      >
        <CheckIcon />
      </div>
    );
  }

  if (state === "failed") {
    return (
      <div
        className="flex-shrink-0 flex items-center justify-center"
        style={{
          width: "1.75rem",
          height: "1.75rem",
          borderRadius: "9999px",
          background: "var(--color-red)",
        }}
      >
        <ErrorIcon />
      </div>
    );
  }

  if (state === "active") {
    return (
      <div
        className="upload-step-active flex-shrink-0 flex items-center justify-center text-sm"
        style={{
          width: "1.75rem",
          height: "1.75rem",
          borderRadius: "9999px",
          background: "rgba(99,102,241,0.2)",
          border: "1.5px solid var(--color-accent)",
          boxShadow: "0 0 12px rgba(99,102,241,0.35)",
        }}
        aria-hidden="true"
      >
        {icon}
      </div>
    );
  }

  return (
    <div
      className="flex-shrink-0 flex items-center justify-center text-xs opacity-40"
      style={{
        width: "1.75rem",
        height: "1.75rem",
        borderRadius: "9999px",
        border: "1.5px solid var(--color-border)",
        background: "var(--color-bg)",
      }}
      aria-hidden="true"
    >
      {icon}
    </div>
  );
}

export function ResumeUploadProgress({
  status,
  filename,
  errorMessage,
  onDismiss,
}: ResumeUploadProgressProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [displayIndex, setDisplayIndex] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const dismissRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const staggerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (status === "uploading") {
      setActiveIndex(0);
      setDisplayIndex(0);
    }
  }, [status, filename]);

  useEffect(() => {
    if (status !== "uploading") {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    intervalRef.current = setInterval(() => {
      setActiveIndex((prev) => Math.min(prev + 1, UPLOAD_STEPS.length - 1));
    }, STEP_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [status]);

  useEffect(() => {
    if (status !== "success") return;

    const startIndex = activeIndex;
    setDisplayIndex(startIndex);

    if (startIndex >= UPLOAD_STEPS.length - 1) {
      dismissRef.current = setTimeout(() => onDismiss?.(), SUCCESS_DISMISS_MS);
      return () => {
        if (dismissRef.current) clearTimeout(dismissRef.current);
      };
    }

    let step = startIndex;
    const tick = () => {
      step += 1;
      setDisplayIndex(step);
      if (step >= UPLOAD_STEPS.length - 1) {
        dismissRef.current = setTimeout(() => onDismiss?.(), SUCCESS_DISMISS_MS);
      } else {
        staggerRef.current = setTimeout(tick, COMPLETE_STAGGER_MS);
      }
    };

    staggerRef.current = setTimeout(tick, COMPLETE_STAGGER_MS);

    return () => {
      if (staggerRef.current) clearTimeout(staggerRef.current);
      if (dismissRef.current) clearTimeout(dismissRef.current);
    };
  }, [status, activeIndex, onDismiss]);

  const effectiveIndex = status === "success" ? displayIndex : activeIndex;
  const progressPercent = Math.round(
    ((effectiveIndex + (status === "success" ? 1 : 0)) / UPLOAD_STEPS.length) * 100,
  );
  const clampedPercent = Math.min(progressPercent, 100);

  const stepsRemaining = Math.max(0, UPLOAD_STEPS.length - 1 - effectiveIndex);
  const estimatedSeconds =
    status === "uploading" ? Math.max(1, Math.ceil(stepsRemaining * 1.5)) : 0;

  const headerBadge =
    status === "success"
      ? { label: "Complete", color: "var(--color-green)" }
      : status === "error"
        ? { label: "Failed", color: "var(--color-red)" }
        : { label: "Processing", color: "var(--color-accent)" };

  return (
    <Card
      padding="none"
      className="card-elevated overflow-hidden fade-up mt-4"
      role="status"
      aria-live="polite"
      aria-label="Resume upload progress"
    >
      <div
        className="px-5 py-4"
        style={{
          borderBottom: "1px solid var(--color-border)",
          background:
            "linear-gradient(135deg, rgba(99,102,241,0.1) 0%, transparent 55%)",
        }}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <div
              className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${status === "uploading" ? "upload-agent-glow" : ""}`}
              style={{
                background: "rgba(99,102,241,0.15)",
                color: "var(--color-accent-h)",
                border: "1px solid rgba(99,102,241,0.25)",
              }}
            >
              <AgentIcon />
            </div>
            <div className="min-w-0">
              <p
                className="text-sm font-semibold"
                style={{ color: "var(--color-text)" }}
              >
                AI Resume Agent
              </p>
              <p
                className="text-xs mt-0.5 truncate"
                style={{ color: "var(--color-subtle)" }}
                title={filename}
              >
                {filename ?? "Processing resume"}
              </p>
            </div>
          </div>
          <span
            className="text-[0.65rem] font-semibold px-2.5 py-1 rounded-full flex-shrink-0 uppercase tracking-wide"
            style={{
              color: headerBadge.color,
              background: `color-mix(in srgb, ${headerBadge.color} 12%, transparent)`,
              border: `1px solid color-mix(in srgb, ${headerBadge.color} 25%, transparent)`,
            }}
          >
            {headerBadge.label}
          </span>
        </div>

        <div className="mt-4">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium" style={{ color: "var(--color-text)" }}>
              {clampedPercent}% complete
            </span>
            {status === "uploading" && (
              <span className="text-xs" style={{ color: "var(--color-muted)" }}>
                ~{estimatedSeconds}s remaining
              </span>
            )}
          </div>
          <div
            className="h-1.5 rounded-full overflow-hidden"
            style={{ background: "var(--color-bg)" }}
          >
            <div
              className="h-full rounded-full transition-all duration-500 ease-out"
              style={{
                width: `${clampedPercent}%`,
                background:
                  status === "error"
                    ? "var(--color-red)"
                    : status === "success"
                      ? "var(--color-green)"
                      : "linear-gradient(90deg, var(--color-accent), var(--color-accent-h))",
                boxShadow:
                  status === "uploading"
                    ? "0 0 12px rgba(99,102,241,0.5)"
                    : undefined,
              }}
            />
          </div>
        </div>
      </div>

      <div className="px-5 py-4">
        <p
          className="text-[0.65rem] uppercase tracking-wider font-semibold mb-3"
          style={{ color: "var(--color-muted)" }}
        >
          Workflow
        </p>

        <ol className="flex flex-col" aria-label="Upload steps">
          {UPLOAD_STEPS.map((step, index) => {
            const stepState = getStepState(index, effectiveIndex, status);
            const isLast = index === UPLOAD_STEPS.length - 1;

            return (
              <li key={step.label} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <StepNode state={stepState} icon={step.icon} />
                  {!isLast && (
                    <div
                      className="flex-1 my-1"
                      style={{
                        width: "2px",
                        minHeight: "1.5rem",
                        background: connectorColor(index, effectiveIndex, status),
                        transition: "background 250ms ease",
                      }}
                    />
                  )}
                </div>

                <div className={`pb-3.5 ${isLast ? "pb-0" : ""} min-w-0 flex-1 pt-0.5`}>
                  <p
                    className="text-sm leading-5"
                    style={{
                      color:
                        stepState === "pending"
                          ? "var(--color-muted)"
                          : stepState === "failed"
                            ? "var(--color-red)"
                            : "var(--color-text)",
                      fontWeight: stepState === "active" ? 500 : 400,
                      opacity: stepState === "pending" ? 0.55 : 1,
                      transition: "color 200ms ease, opacity 200ms ease",
                    }}
                  >
                    {step.label}
                    {stepState === "active" && status === "uploading" && (
                      <span
                        className="inline-block ml-1.5 upload-dots"
                        style={{ color: "var(--color-accent-h)" }}
                        aria-hidden="true"
                      >
                        …
                      </span>
                    )}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>

        {status === "error" && errorMessage && (
          <div
            className="mt-2 px-3 py-2.5 rounded-lg text-sm"
            style={{
              color: "var(--color-red)",
              background: "rgba(239, 68, 68, 0.08)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
            }}
          >
            {errorMessage}
          </div>
        )}

        {status === "success" && (
          <p
            className="mt-2 text-xs text-center"
            style={{ color: "var(--color-green)" }}
          >
            Resume profile ready — updating dashboard…
          </p>
        )}
      </div>
    </Card>
  );
}
